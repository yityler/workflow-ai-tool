from dataclasses import dataclass

@dataclass
class Calculator:
    """Basic calculator class"""
    def add(self, a: float, b: float) -> float:
        """Add two numbers together"""
        return a + b
    
    def subtract(self, a: float, b: float) -> float:
        """Subtract one number from another"""
        return a - b
    
    def multiply(self, a: float, b: float) -> float:
        """Multiply two numbers together"""
        return a * b
    
    def divide(self, a: float, b: float) -> float:
        """Divide one number by another"""
        if b == 0:
            raise ValueError("Cannot divide by zero")
        return a / b