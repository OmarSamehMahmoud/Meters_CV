import torch
from src.watermeter.digit_model import TinyDigitCNN

def test_tiny_digit_cnn_output_shape():
    model=TinyDigitCNN()
    output=model(torch.zeros(2,1,48,32))
    assert tuple(output.shape)==(2,10)
