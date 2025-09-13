import os, io, json, base64
import boto3, numpy as np, cv2, fitz  # PyMuPDF
s3 = boto3.client("s3")

# ---------- 快速去红：HSV守护版 ----------
def remove_red_hsv_guarded(bgr, gray_gate=185):
    hsv = cv2.cvtColor(bgr, cv2.COLOR_BGR2HSV)
    mask = cv2.inRange(hsv, (0,50,60), (12,255,255)) | cv2.inRange(hsv, (170,50,60), (180,255,255))
    gray0 = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
    edges = cv2.Canny(gray0, 60, 160)
    edges = cv2.dilate(edges, cv2.getStructuringElement(cv2.MORPH_RECT, (3,3)), 1)
    mask = cv2.erode(mask, cv2.getStructuringElement(cv2.MORPH_RECT, (2,2)), 1)
    safe = cv2.bitwise_and(mask, (gray0 > gray_gate).astype(np.uint8) * 255)
    safe = cv2.bitwise_and(safe, cv2.bitwise_not(edges))
    out = bgr.copy()
    out[safe > 0] = (255,255,255)
    return cv2.cvtColor(out, cv2.COLOR_BGR2GRAY)

# ---------- 备选：通道抑制（更快） ----------
def remove_red_channel_fast(bgr, alpha=0.5):
    b, g, r = cv2.split(bgr)
    gb = cv2.max(g, b).astype(np.int16)
    gray = np.clip(gb - (alpha * r.astype(np.int16)), 0, 255).astype(np.uint8)
    return gray

# ---------- 角度估计（25%小图） ----------
def estimate_angle_fast(bgr_small):
    g = cv2.cvtColor(bgr_small, cv2.COLOR_BGR2GRAY)
    edges = cv2.Canny(g, 50, 150)
    lines = cv2.HoughLines(edges, 1, np.pi/180, 120)
    if lines is None: return 0.0
    angs = []
    for rho, theta in lines[:,0]:
        ang = (theta * 180 / np.pi) - 90
        if -10 <= ang <= 10: angs.append(ang)
    return float(np.median(angs)) if angs else 0.0

# ---------- 红线残留估计（是否切换备选路径） ----------
def red_line_residual(gray):
    inv = 255 - gray
    k_h = cv2.getStructuringElement(cv2.MORPH_RECT, (25,1))
    k_v = cv2.getStructuringElement(cv2.MORPH_RECT, (1,25))
    mh = cv2.morphologyEx(inv, cv2.MORPH_OPEN, k_h, 1)
    mv = cv2.morphologyEx(inv, cv2.MORPH_OPEN, k_v, 1)
    lines = cv2.max(mh, mv)
    return (lines > 0).mean()

# ---------- 单页预处理（内存流、无落盘） ----------
def preprocess_page(bgr):
    # 小图估角度 → 大图旋转（一次）
    small = cv2.resize(bgr, None, fx=0.25, fy=0.25, interpolation=cv2.INTER_AREA)
    angle = estimate_angle_fast(small)
    h, w = bgr.shape[:2]
    M = cv2.getRotationMatrix2D((w/2, h/2), angle, 1.0)
    bgr = cv2.warpAffine(bgr, M, (w, h), flags=cv2.INTER_LINEAR,
                         borderMode=cv2.BORDER_CONSTANT, borderValue=(255,255,255))

    # 快速红量探测（Lab a*）
    a = cv2.cvtColor(bgr, cv2.COLOR_BGR2LAB)[:,:,1]
    if (a > 135).mean() < 0.01:
        gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
    else:
        gray = remove_red_hsv_guarded(bgr)  # 默认路径
        if red_line_residual(gray) > 0.006:  # 仍有细线 → 改用通道抑制
            gray = remove_red_channel_fast(bgr, alpha=0.5)

    # 自适应阈值（快、稳）
    bw = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                               cv2.THRESH_BINARY, 35, 15)
    # 轻度闭运算修补断笔
    bw = cv2.morphologyEx(bw, cv2.MORPH_CLOSE,
                          cv2.getStructuringElement(cv2.MORPH_RECT, (2,2)), 1)
    return bw

# ---------- S3 工具 ----------
def get_s3_bytes(bucket, key):
    obj = s3.get_object(Bucket=bucket, Key=key)
    return obj["Body"].read()

def put_png_s3(bucket, key, img):
    ok, buf = cv2.imencode(".png", img)
    s3.put_object(Bucket=bucket, Key=key, Body=buf.tobytes(), ContentType="image/png")

# ---------- PDF 字节 → 按页渲染 → 预处理 → 存 S3 ----------
def process_pdf_bytes_to_s3(pdf_bytes, out_bucket, out_prefix, dpi=300, page_from=1, page_to=None):
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    n_pages = doc.page_count
    end = page_to or n_pages
    for i in range(page_from, end + 1):
        page = doc.load_page(i - 1)
        # DPI→缩放矩阵（72dpi 基准）
        zoom = dpi / 72.0
        mat = fitz.Matrix(zoom, zoom)
        pix = page.get_pixmap(matrix=mat, alpha=False)  # RGB
        arr = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width, pix.n)
        bgr = cv2.cvtColor(arr, cv2.COLOR_RGB2BGR)

        bw = preprocess_page(bgr)
        out_key = f"{out_prefix.rstrip('/')}/page-{i:03d}.png"
        put_png_s3(out_bucket, out_key, bw)

# ---------- Lambda 入口（S3 put 触发） ----------
def lambda_handler(event, context):
    # 约定环境变量：OUTPUT_BUCKET, OUTPUT_PREFIX_BASE, DPI
    out_bucket = os.environ.get("OUTPUT_BUCKET")
    base_prefix = os.environ.get("OUTPUT_PREFIX_BASE", "processed/")
    dpi = int(os.environ.get("DPI", "300"))

    for rec in event.get("Records", []):
        bucket = rec["s3"]["bucket"]["name"]
        key = rec["s3"]["object"]["key"]
        pdf_bytes = get_s3_bytes(bucket, key)
        # 以输入路径构造输出前缀（同目录名）
        prefix = f"{base_prefix.rstrip('/')}/{os.path.basename(key)}"
        process_pdf_bytes_to_s3(pdf_bytes, out_bucket or bucket, prefix, dpi=dpi)

    return {"ok": True}
