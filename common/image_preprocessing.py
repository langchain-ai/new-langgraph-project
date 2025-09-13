"""PDF图像预处理模块，用于优化OCR识别率。

主要功能：
1. 去除红色底纹（HSV守护版 + 通道抑制备选）
2. 自动角度纠正
3. 自适应二值化
4. 形态学修复

专门针对医疗表单（如CMS-1500）的扫描件优化。
"""

import logging
from typing import List, Tuple, Optional
import numpy as np
import cv2
import fitz  # PyMuPDF

logger = logging.getLogger(__name__)


class PDFImagePreprocessor:
    """PDF图像预处理器，优化OCR识别效果。"""
    
    # 安全限制
    MAX_PAGES = 3  # 最多处理3页
    MAX_FILE_SIZE = 12 * 1024 * 1024  # 12MB文件大小限制
    MAX_IMAGE_BYTES = 10 * 1024 * 1024  # Textract单图像10MB限制
    
    def __init__(self, dpi: int = 300, remove_red: bool = True, auto_rotate: bool = True):
        """初始化预处理器。
        
        Args:
            dpi: 渲染分辨率，默认300
            remove_red: 是否去除红色底纹，默认True
            auto_rotate: 是否自动纠正角度，默认True
        """
        self.dpi = dpi
        self.remove_red = remove_red
        self.auto_rotate = auto_rotate
        self.gray_gate = 185  # 灰度门限
        
    def preprocess_pdf_bytes(self, pdf_bytes: bytes) -> List[Tuple[np.ndarray, bytes]]:
        """处理PDF字节流，返回预处理后的图像和PNG字节。
        
        Args:
            pdf_bytes: PDF文件字节
            
        Returns:
            列表，每项包含(numpy数组, PNG字节)
            
        Raises:
            ValueError: 文件过大或处理失败
        """
        # 检查文件大小
        if len(pdf_bytes) > self.MAX_FILE_SIZE:
            raise ValueError(
                f"PDF文件过大: {len(pdf_bytes)/1024/1024:.1f}MB，"
                f"最大限制 {self.MAX_FILE_SIZE/1024/1024}MB"
            )
        
        doc = None
        try:
            # 打开PDF
            doc = fitz.open(stream=pdf_bytes, filetype="pdf")
            
            # 页数限制
            page_count = doc.page_count
            pages_to_process = min(page_count, self.MAX_PAGES)
            
            if page_count > self.MAX_PAGES:
                logger.warning(
                    f"PDF有{page_count}页，仅处理前{self.MAX_PAGES}页"
                )
            
            # 处理每一页
            processed_pages = []
            zoom = self.dpi / 72.0  # DPI转缩放矩阵（72dpi基准）
            mat = fitz.Matrix(zoom, zoom)
            
            for page_num in range(pages_to_process):
                page = None
                pix = None
                try:
                    # 加载页面
                    page = doc.load_page(page_num)
                    
                    # 渲染为图像（RGB）
                    pix = page.get_pixmap(matrix=mat, alpha=False)
                    
                    # 转换为numpy数组
                    arr = np.frombuffer(pix.samples, dtype=np.uint8)
                    arr = arr.reshape(pix.height, pix.width, pix.n)
                    
                    # RGB转BGR（OpenCV格式）
                    bgr = cv2.cvtColor(arr, cv2.COLOR_RGB2BGR)
                    
                    # 预处理
                    logger.info(f"预处理第{page_num + 1}页")
                    bw_image = self.preprocess_page(bgr)
                    
                    # 编码为PNG
                    png_bytes = self.encode_for_textract(bw_image)
                    
                    processed_pages.append((bw_image, png_bytes))
                    
                except Exception as e:
                    logger.error(f"处理第{page_num + 1}页失败: {e}")
                    # 继续处理其他页面
                    
                finally:
                    # 释放页面资源
                    if pix:
                        pix = None
                    if page:
                        page = None
            
            if not processed_pages:
                raise ValueError("没有成功处理任何页面")
            
            return processed_pages
            
        finally:
            # 确保释放PDF文档
            if doc:
                doc.close()
                doc = None
    
    def preprocess_page(self, bgr: np.ndarray) -> np.ndarray:
        """预处理单页图像。
        
        流程：
        1. 角度估计（25%缩放）
        2. 旋转矫正
        3. 红色检测与去除
        4. 自适应二值化
        5. 形态学修复
        
        Args:
            bgr: BGR格式图像
            
        Returns:
            二值化图像（0和255）
        """
        try:
            # 角度纠正
            if self.auto_rotate:
                # 小图估角度
                small = cv2.resize(bgr, None, fx=0.25, fy=0.25, 
                                 interpolation=cv2.INTER_AREA)
                angle = self.estimate_angle_fast(small)
                
                if abs(angle) > 0.5:  # 大于0.5度才旋转
                    logger.info(f"检测到倾斜角度: {angle:.1f}度")
                    h, w = bgr.shape[:2]
                    M = cv2.getRotationMatrix2D((w/2, h/2), angle, 1.0)
                    bgr = cv2.warpAffine(bgr, M, (w, h), 
                                       flags=cv2.INTER_LINEAR,
                                       borderMode=cv2.BORDER_CONSTANT, 
                                       borderValue=(255, 255, 255))
            
            # 去红处理
            if self.remove_red:
                # 快速红量探测（Lab a*通道）
                lab = cv2.cvtColor(bgr, cv2.COLOR_BGR2LAB)
                a_channel = lab[:, :, 1]
                red_ratio = (a_channel > 135).mean()
                
                if red_ratio < 0.01:
                    # 红色很少，直接转灰度
                    gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
                else:
                    logger.info(f"检测到红色底纹（{red_ratio:.1%}），执行去红处理")
                    # HSV守护版去红
                    gray = self.remove_red_hsv_guarded(bgr, self.gray_gate)
                    
                    # 检查残留
                    if self.red_line_residual(gray) > 0.006:
                        logger.info("HSV去红后仍有残留，切换到通道抑制法")
                        gray = self.remove_red_channel_fast(bgr, alpha=0.5)
            else:
                gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
            
            # 自适应阈值二值化
            bw = cv2.adaptiveThreshold(gray, 255, 
                                      cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                                      cv2.THRESH_BINARY, 35, 15)
            
            # 轻度闭运算修补断笔
            kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (2, 2))
            bw = cv2.morphologyEx(bw, cv2.MORPH_CLOSE, kernel, iterations=1)
            
            return bw
            
        except Exception as e:
            logger.error(f"页面预处理失败: {e}")
            # 降级返回灰度图
            return cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
    
    def remove_red_hsv_guarded(self, bgr: np.ndarray, gray_gate: int = 185) -> np.ndarray:
        """HSV守护版去红算法。
        
        通过HSV色彩空间精准定位红色，同时保护边缘和深色文字。
        """
        # 转换到HSV色彩空间
        hsv = cv2.cvtColor(bgr, cv2.COLOR_BGR2HSV)
        
        # 红色在HSV中的范围（考虑环绕）
        mask1 = cv2.inRange(hsv, (0, 50, 60), (12, 255, 255))
        mask2 = cv2.inRange(hsv, (170, 50, 60), (180, 255, 255))
        mask = cv2.bitwise_or(mask1, mask2)
        
        # 转灰度用于边缘检测
        gray0 = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
        
        # Canny边缘检测
        edges = cv2.Canny(gray0, 60, 160)
        edges = cv2.dilate(edges, 
                          cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3)), 
                          iterations=1)
        
        # 收缩红色区域，避免误伤
        mask = cv2.erode(mask, 
                        cv2.getStructuringElement(cv2.MORPH_RECT, (2, 2)), 
                        iterations=1)
        
        # 灰度门限保护（保护深色文字）
        gray_mask = (gray0 > gray_gate).astype(np.uint8) * 255
        safe = cv2.bitwise_and(mask, gray_mask)
        
        # 边缘保护
        safe = cv2.bitwise_and(safe, cv2.bitwise_not(edges))
        
        # 应用去红
        out = bgr.copy()
        out[safe > 0] = (255, 255, 255)
        
        return cv2.cvtColor(out, cv2.COLOR_BGR2GRAY)
    
    def remove_red_channel_fast(self, bgr: np.ndarray, alpha: float = 0.5) -> np.ndarray:
        """通道抑制快速去红（备选方案）。
        
        通过抑制红色通道来去除红色底纹。
        """
        b, g, r = cv2.split(bgr)
        
        # 取绿蓝通道最大值
        gb = cv2.max(g, b).astype(np.int16)
        
        # 抑制红色通道
        gray = np.clip(gb - (alpha * r.astype(np.int16)), 0, 255)
        
        return gray.astype(np.uint8)
    
    def estimate_angle_fast(self, bgr_small: np.ndarray) -> float:
        """快速角度估计（使用25%缩放图）。
        
        Returns:
            旋转角度（度）
        """
        # 转灰度
        gray = cv2.cvtColor(bgr_small, cv2.COLOR_BGR2GRAY)
        
        # 边缘检测
        edges = cv2.Canny(gray, 50, 150)
        
        # 霍夫线检测
        lines = cv2.HoughLines(edges, 1, np.pi/180, 120)
        
        if lines is None:
            return 0.0
        
        # 收集接近水平的线角度
        angles = []
        for rho, theta in lines[:, 0]:
            angle = (theta * 180 / np.pi) - 90
            if -10 <= angle <= 10:  # 只考虑接近水平的线
                angles.append(angle)
        
        # 返回中位数角度
        return float(np.median(angles)) if angles else 0.0
    
    def red_line_residual(self, gray: np.ndarray) -> float:
        """检测红线残留（用于判断是否切换备选算法）。
        
        Returns:
            残留比例（0-1）
        """
        # 反转图像（黑底白字）
        inv = 255 - gray
        
        # 水平和垂直结构元素
        k_h = cv2.getStructuringElement(cv2.MORPH_RECT, (25, 1))
        k_v = cv2.getStructuringElement(cv2.MORPH_RECT, (1, 25))
        
        # 形态学开运算提取线条
        mh = cv2.morphologyEx(inv, cv2.MORPH_OPEN, k_h, iterations=1)
        mv = cv2.morphologyEx(inv, cv2.MORPH_OPEN, k_v, iterations=1)
        
        # 合并水平和垂直线
        lines = cv2.max(mh, mv)
        
        # 计算残留比例
        return (lines > 0).mean()
    
    def encode_for_textract(self, image: np.ndarray) -> bytes:
        """为Textract编码图像。
        
        二值图像使用PNG格式（无损压缩，文件更小）。
        
        Args:
            image: 预处理后的图像
            
        Returns:
            PNG编码的字节
        """
        # 检查是否为二值图像
        unique_values = np.unique(image)
        is_binary = len(unique_values) <= 2
        
        if is_binary:
            # 二值图像：使用PNG（最佳选择）
            encode_param = [cv2.IMWRITE_PNG_COMPRESSION, 9]  # 最大压缩
            _, buffer = cv2.imencode('.png', image, encode_param)
        else:
            # 灰度图像：先尝试PNG
            _, buffer = cv2.imencode('.png', image)
            
            # 如果太大，降级到高质量JPEG
            if len(buffer) > 5 * 1024 * 1024:  # 5MB
                encode_param = [cv2.IMWRITE_JPEG_QUALITY, 95]
                _, buffer = cv2.imencode('.jpg', image, encode_param)
        
        image_bytes = buffer.tobytes()
        
        # 检查大小限制
        if len(image_bytes) > self.MAX_IMAGE_BYTES:
            logger.warning(
                f"编码后图像过大: {len(image_bytes)/1024/1024:.1f}MB，"
                "尝试降低质量"
            )
            # 降低JPEG质量
            encode_param = [cv2.IMWRITE_JPEG_QUALITY, 85]
            _, buffer = cv2.imencode('.jpg', image, encode_param)
            image_bytes = buffer.tobytes()
        
        logger.info(f"图像编码完成: {len(image_bytes)/1024:.1f}KB")
        return image_bytes