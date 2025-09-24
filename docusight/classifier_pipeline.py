import io
import sys

from fastapi import FastAPI
from transformers import AutoModelForSequenceClassification, AutoTokenizer, pipeline

from docusight.config import settings
from docusight.logging import logger


def setup_pipeline(app: FastAPI):
    stdout_buffer = io.StringIO()
    old_stdout = sys.stdout
    sys.stdout = stdout_buffer
    try:
        tokenizer = AutoTokenizer.from_pretrained(settings.CLASSIFICATION_MODEL_NAME)
        model = AutoModelForSequenceClassification.from_pretrained(
            settings.CLASSIFICATION_MODEL_NAME
        )

        sentiment_classifier = pipeline(
            "sentiment-analysis",
            model=model,
            tokenizer=tokenizer,
            device=settings.GPU_DEVICE,
        )

        # # TODO: pre-compile model for faster inference (PyTorch 2.0+, CUDA > 7.0)
        # model = torch.compile(model)
        # sentiment_classifier.model = model

        # Store in app state for access in endpoints
        app.state.sentiment_classifier = sentiment_classifier

    finally:
        sys.stdout = old_stdout

    # Log any output from pipeline instantiation
    cuda_message = stdout_buffer.getvalue().strip()
    if cuda_message:
        logger.info(f"HuggingFace pipeline: {cuda_message}")
