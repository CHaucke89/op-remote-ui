#ifndef MOCK_OPENPILOT_FIXED_H
#define MOCK_OPENPILOT_FIXED_H

#include <QObject>
#include <QString>
#include <QDebug>
#include <QApplication>
#include <QWidget>
#include <QMainWindow>
#include <QTimer>
#include <QLabel>
#include <QVBoxLayout>
#include <QHBoxLayout>
#include <QPaintEvent>
#include <QPainter>
#include <QBrush>
#include <QPen>
#include <QFont>
#include <QDateTime>
#include <QEventLoop>
#include <cstdlib>
#include <cmath>

// Mock OpenPilot dependencies
namespace {
  void swagLogMessageHandler(QtMsgType type, const QMessageLogContext &, const QString &msg) {
    QTextStream stream(stdout);
    stream << "[" << QDateTime::currentDateTime().toString("hh:mm:ss.zzz") << "] ";
    switch (type) {
      case QtDebugMsg:    stream << "DEBUG: "; break;
      case QtWarningMsg:  stream << "WARN:  "; break;
      case QtCriticalMsg: stream << "CRIT:  "; break;
      case QtFatalMsg:    stream << "FATAL: "; break;
      case QtInfoMsg:     stream << "INFO:  "; break;
    }
    stream << msg << Qt::endl;
  }

  void initApp(int argc, char *argv[]) {
    Q_UNUSED(argc)
    Q_UNUSED(argv)
    // Mock initialization
    qDebug() << "Mock OpenPilot app initialized";
  }
}

// Mock Params class
class Params {
public:
  QString get(const QString &key) {
    if (key == "LanguageSetting") {
      return "en_US";
    }
    return "";
  }
};

// Central widget that handles all the painting
class OpenPilotWidget : public QWidget {
  Q_OBJECT

public:
  OpenPilotWidget(QWidget *parent = nullptr) : QWidget(parent) {
    setFixedSize(2160, 1080);

    // Initialize mock values
    speed_ = 35;
    lane_offset_ = 0.0;
    engaged_ = true;

    // Set up animation timer
    update_timer_ = new QTimer(this);
    connect(update_timer_, &QTimer::timeout, this, &OpenPilotWidget::updateAnimation);
    update_timer_->start(100); // 10 FPS animation

    qDebug() << "OpenPilot widget initialized with size:" << size();
  }

protected:
  void paintEvent(QPaintEvent *event) override {
    Q_UNUSED(event)

    QPainter painter(this);
    painter.setRenderHint(QPainter::Antialiasing);

    // Fill background
    painter.fillRect(rect(), Qt::black);

    // Draw all UI elements
    drawTopBar(painter);
    drawRoadView(painter);
    drawSpeedIndicator(painter);
    drawStatusIndicators(painter);
    drawAlerts(painter);
  }

private slots:
  void updateAnimation() {
    static int counter = 0;
    counter++;

    // Update speed and other dynamic elements
    speed_ = 30 + (counter % 40);  // Speed varies from 30-70

    // Update lane position
    lane_offset_ = sin(counter * 0.1) * 0.3;  // Simulate lane changes

    // Update engagement status occasionally
    if (counter % 100 == 0) {
      engaged_ = !engaged_;
    }

    update();  // Trigger repaint
  }

private:
  void drawTopBar(QPainter &painter) {
    // Top bar background
    painter.fillRect(0, 0, 2160, 120, QColor(20, 20, 30));

    painter.setPen(QPen(Qt::white, 2));
    painter.setFont(QFont("Arial", 28));

    // Time
    QString time_str = QDateTime::currentDateTime().toString("hh:mm:ss");
    painter.drawText(50, 60, time_str);

    // Status
    QString status = engaged_ ? "ENGAGED" : "DISENGAGED";
    painter.setPen(engaged_ ? Qt::green : Qt::red);
    painter.setFont(QFont("Arial", 32, QFont::Bold));
    painter.drawText(1600, 70, status);

    // Title
    painter.setPen(Qt::white);
    painter.setFont(QFont("Arial", 24));
    painter.drawText(900, 60, "OpenPilot UI Simulator");
  }

  void drawRoadView(QPainter &painter) {
    // Road background
    QRect road_area(300, 200, 1560, 700);
    painter.fillRect(road_area, QColor(40, 40, 40));

    // Draw horizon line
    painter.setPen(QPen(Qt::gray, 2));
    painter.drawLine(300, 400, 1860, 400);

    // Lane lines
    painter.setPen(QPen(Qt::yellow, 8));

    // Left lane
    int left_x = 600 + (int)(lane_offset_ * 200);
    for (int y = 300; y < 900; y += 60) {
      painter.drawLine(left_x, y, left_x, y + 30);
    }

    // Right lane
    int right_x = 1560 + (int)(lane_offset_ * 200);
    for (int y = 300; y < 900; y += 60) {
      painter.drawLine(right_x, y, right_x, y + 30);
    }

    // Center line (dashed)
    painter.setPen(QPen(Qt::white, 6));
    for (int y = 300; y < 900; y += 40) {
      painter.drawLine(1080, y, 1080, y + 25);
    }

    // Vehicle representation (our car)
    painter.fillRect(1000, 750, 160, 80, QColor(0, 120, 200));
    painter.setPen(QPen(Qt::white, 2));
    painter.drawRect(1000, 750, 160, 80);

    // Draw some "other cars"
    painter.fillRect(800, 600, 100, 60, QColor(200, 0, 0));
    painter.fillRect(1300, 650, 100, 60, QColor(150, 150, 0));
  }

  void drawSpeedIndicator(QPainter &painter) {
    // Speed circle background
    painter.fillEllipse(50, 300, 250, 250, QColor(0, 0, 0, 150));

    // Speed circle
    painter.setPen(QPen(Qt::white, 6));
    painter.drawEllipse(50, 300, 250, 250);

    // Speed text
    painter.setPen(Qt::white);
    painter.setFont(QFont("Arial", 56, QFont::Bold));

    QRect speed_rect(50, 380, 250, 80);
    painter.drawText(speed_rect, Qt::AlignCenter, QString::number(speed_));

    // MPH label
    painter.setFont(QFont("Arial", 20));
    QRect mph_rect(50, 460, 250, 30);
    painter.drawText(mph_rect, Qt::AlignCenter, "MPH");
  }

  void drawStatusIndicators(QPainter &painter) {
    // Status panel background
    painter.fillRect(1900, 300, 240, 200, QColor(0, 0, 0, 150));
    painter.setPen(QPen(Qt::white, 2));
    painter.drawRect(1900, 300, 240, 200);

    // Status indicators
    QStringList statuses = {"GPS: GOOD", "TEMP: 45°C", "MEM: 60%", "NET: OK"};
    QList<QColor> colors = {Qt::green, Qt::yellow, Qt::cyan, Qt::green};

    painter.setFont(QFont("Arial", 16));

    for (int i = 0; i < statuses.size(); ++i) {
      painter.setPen(colors[i]);
      painter.drawText(1910, 330 + i * 35, statuses[i]);
    }
  }

  void drawAlerts(QPainter &painter) {
    static int alert_counter = 0;
    alert_counter++;

    // Show alert occasionally
    if ((alert_counter / 30) % 8 < 2) {  // Show alert 2/8 of the time
      QRect alert_rect(700, 450, 760, 120);

      // Alert background
      painter.fillRect(alert_rect, QColor(255, 100, 0, 200));
      painter.setPen(QPen(Qt::white, 4));
      painter.drawRect(alert_rect);

      // Alert text
      painter.setPen(Qt::white);
      painter.setFont(QFont("Arial", 32, QFont::Bold));
      painter.drawText(alert_rect, Qt::AlignCenter, "SLOW DOWN");

      // Blinking effect
      if ((alert_counter / 10) % 2 == 0) {
        painter.fillRect(alert_rect, QColor(255, 255, 255, 50));
      }
    }

    // Draw distance to lead car
    painter.setPen(Qt::white);
    painter.setFont(QFont("Arial", 20));
    painter.drawText(50, 950, QString("Lead: %1m").arg(25 + (alert_counter % 50)));
  }

private:
  QTimer *update_timer_;
  int speed_;
  double lane_offset_;
  bool engaged_;
};

// Mock MainWindow class that simulates OpenPilot UI
class MainWindow : public QMainWindow {
  Q_OBJECT

public:
  MainWindow(QWidget *parent = nullptr) : QMainWindow(parent) {
    qDebug() << "Creating MainWindow...";

    setFixedSize(2160, 1080);
    setWindowTitle("Mock OpenPilot UI - Real-Time Display");

    // Create central widget
    ui_widget_ = new OpenPilotWidget();
    setCentralWidget(ui_widget_);

    qDebug() << "MainWindow setup complete";
  }

  // Mock the grab() function that captures screenshots
  QPixmap grab() {
    // Capture the actual rendered widget
    return ui_widget_->grab();
  }

private:
  OpenPilotWidget *ui_widget_;
};

// Mock function to set main window reference
static MainWindow* g_main_window = nullptr;

inline void setMainWindow(MainWindow* window) {
  g_main_window = window;
}

// MOC file will be generated automatically

#endif // MOCK_OPENPILOT_FIXED_H