#include "frame_streamer.h"
#include <QWidget>
#include <QTimer>
#include <QPixmap>
#include <QBuffer>
#include <QDateTime>
#include <QDebug>
#include <sys/mman.h>
#include <sys/stat.h>
#include <fcntl.h>
#include <unistd.h>
#include <cstring>

FrameStreamer::FrameStreamer(QWidget* window, QObject* parent)
    : QObject(parent), window_(window), timer_(nullptr),
      shared_frame_(nullptr), shm_fd_(-1), shm_ptr_(nullptr) {
  timer_ = new QTimer(this);
  connect(timer_, &QTimer::timeout, this, &FrameStreamer::captureFrame);
  initSharedMemory();
}

FrameStreamer::~FrameStreamer() {
  stop();
  cleanupSharedMemory();
}

void FrameStreamer::initSharedMemory() {
  // Remove any existing shared memory
  shm_unlink(SHM_NAME);

  // Create shared memory
  shm_fd_ = shm_open(SHM_NAME, O_CREAT | O_RDWR, 0666);
  if (shm_fd_ == -1) {
    qCritical() << "Failed to create shared memory";
    return;
  }

  // Set size
  if (ftruncate(shm_fd_, SHM_SIZE) == -1) {
    qCritical() << "Failed to set shared memory size";
    close(shm_fd_);
    shm_fd_ = -1;
    return;
  }

  // Map memory
  shm_ptr_ = mmap(nullptr, SHM_SIZE, PROT_READ | PROT_WRITE, MAP_SHARED, shm_fd_, 0);
  if (shm_ptr_ == MAP_FAILED) {
    qCritical() << "Failed to map shared memory";
    close(shm_fd_);
    shm_fd_ = -1;
    shm_ptr_ = nullptr;
    return;
  }

  // Initialize the shared frame structure
  shared_frame_ = static_cast<SharedFrame*>(shm_ptr_);
  new (shared_frame_) SharedFrame();

  qDebug() << "Shared memory initialized at" << SHM_NAME;
}

void FrameStreamer::cleanupSharedMemory() {
  if (shm_ptr_ && shm_ptr_ != MAP_FAILED) {
    munmap(shm_ptr_, SHM_SIZE);
  }
  if (shm_fd_ != -1) {
    close(shm_fd_);
  }
  shm_unlink(SHM_NAME);
}

void FrameStreamer::start() {
  if (!timer_ || !shared_frame_) return;
  timer_->start(500);  // 2 FPS for lower resource usage
  qDebug() << "Frame streaming started";
}

void FrameStreamer::stop() {
  if (timer_) {
    timer_->stop();
  }
  qDebug() << "Frame streaming stopped";
}

void FrameStreamer::captureFrame() {
  if (!window_ || !shared_frame_) return;

  QMutexLocker locker(&mutex_);

  // Capture the window
  QPixmap pixmap = window_->grab();
  if (pixmap.isNull()) {
    qWarning() << "Failed to capture frame";
    return;
  }

  // Convert to JPEG for compression
  QByteArray jpeg_data;
  QBuffer buffer(&jpeg_data);
  buffer.open(QIODevice::WriteOnly);

  // Save as JPEG with 85% quality (good balance of quality vs size)
  if (!pixmap.save(&buffer, "JPEG", 85)) {
    qWarning() << "Failed to encode frame as JPEG";
    return;
  }

  // Check size
  if (jpeg_data.size() > static_cast<int>(sizeof(shared_frame_->data))) {
    qWarning() << "Frame too large:" << jpeg_data.size() << "bytes";
    return;
  }

  // Mark as not ready while updating
  shared_frame_->ready.store(false);

  // Update metadata
  shared_frame_->timestamp.store(QDateTime::currentMSecsSinceEpoch());
  shared_frame_->width.store(pixmap.width());
  shared_frame_->height.store(pixmap.height());
  shared_frame_->size.store(jpeg_data.size());
  shared_frame_->format.store(1);  // 1 = JPEG

  // Copy data
  memcpy(shared_frame_->data, jpeg_data.data(), jpeg_data.size());

  // Mark as ready
  shared_frame_->ready.store(true);

  qDebug() << "Frame captured:" << jpeg_data.size() << "bytes, "
           << pixmap.width() << "x" << pixmap.height();
}