from ..schemas import AgentOutput, ValidationResult

class StructureValidator:
    """Validates that agent output complies with the strict JSON protocol."""
    
    def validate(self, output: AgentOutput) -> ValidationResult:
        if not output.status in ["PASS", "FAIL", "WARNING"]:
            return ValidationResult(
                is_valid=False,
                retry_message=f"Invalid status '{output.status}'. Must be PASS, FAIL, or WARNING."
            )
        
        if output.confidence_score < 0.0 or output.confidence_score > 1.0:
             return ValidationResult(
                is_valid=False,
                retry_message=f"Invalid confidence score {output.confidence_score}. Must be between 0.0 and 1.0."
            )

        if output.status == "FAIL" and not output.comments:
             return ValidationResult(
                is_valid=False,
                retry_message="Status is FAIL but no comments were provided. explain why."
            )
            
        return ValidationResult(is_valid=True)
