diff --git a/Dockerfile b/Dockerfile
new file mode 100644
index 0000000000000000000000000000000000000000..36d03720beb847267c70104912068eeea52244cc
--- /dev/null
+++ b/Dockerfile
@@ -0,0 +1,19 @@
+FROM python:3.11-slim
+
+RUN apt-get update \ 
+    && apt-get install -y --no-install-recommends \
+        tesseract-ocr \
+        tesseract-ocr-eng \
+        tesseract-ocr-spa \
+        poppler-utils \
+        imagemagick \ 
+    && rm -rf /var/lib/apt/lists/*
+
+WORKDIR /app
+COPY requirements.txt ./
+RUN pip install --no-cache-dir -r requirements.txt
+
+COPY . .
+
+ENV PORT=8000
+CMD ["uvicorn", "ai_translator.api:app", "--host", "0.0.0.0", "--port", "${PORT}"]
