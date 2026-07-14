"""YOLO 检测配置。"""

# 检测模型默认配置
DEFAULT_CONF_THRESHOLD = 0.25
DEFAULT_IOU_THRESHOLD = 0.45
DEFAULT_IMAGE_SIZE = 640

# Keep this in sync with the browser upload control.  TIFF was supported by the
# existing UI, while WebP is useful for modern browser uploads.
ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/bmp", "image/tiff", "image/webp"}
MAX_IMAGE_SIZE = 10 * 1024 * 1024
MAX_BATCH_SIZE = 20
