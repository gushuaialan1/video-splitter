import sys
from PyQt5 import QtWidgets, QtGui
from PyQt5.QtWidgets import QApplication, QMainWindow, QLabel, QPushButton, QVBoxLayout, QFileDialog, QLineEdit, QMessageBox, QWidget
import os
import tempfile
from pydub import AudioSegment
import subprocess

class VideoSplitterApp(QMainWindow):
    def __init__(self):
        super(VideoSplitterApp, self).__init__()
        self.setWindowTitle("视频分割器")
        self.setGeometry(200, 200, 500, 400)
        self.initUI()

    def initUI(self):
        layout = QVBoxLayout()

        # Labels and inputs
        self.video_path_label = QLabel("视频路径: ")
        layout.addWidget(self.video_path_label)

        self.browse_button = QPushButton("选择视频")
        self.browse_button.clicked.connect(self.browse_video)
        layout.addWidget(self.browse_button)

        self.parts_label = QLabel("分割的部分数量:")
        layout.addWidget(self.parts_label)

        self.parts_input = QLineEdit()
        self.parts_input.setPlaceholderText("请输入分割的部分数量")
        layout.addWidget(self.parts_input)

        self.threshold_label = QLabel("音频阈值 (默认 -35dB):")
        layout.addWidget(self.threshold_label)

        self.threshold_input = QLineEdit()
        self.threshold_input.setPlaceholderText("请输入音频阈值")
        layout.addWidget(self.threshold_input)

        self.prefix_label = QLabel("输出文件名前缀:")
        layout.addWidget(self.prefix_label)

        self.prefix_input = QLineEdit()
        self.prefix_input.setPlaceholderText("请输入文件名前缀")
        layout.addWidget(self.prefix_input)

        self.output_folder_label = QLabel("输出文件夹: ")
        layout.addWidget(self.output_folder_label)

        self.browse_output_button = QPushButton("选择输出文件夹")
        self.browse_output_button.clicked.connect(self.browse_output_folder)
        layout.addWidget(self.browse_output_button)

        # Split Button
        self.split_button = QPushButton("分割视频")
        self.split_button.clicked.connect(self.split_video)
        layout.addWidget(self.split_button)

        container = QWidget()
        container.setLayout(layout)
        self.setCentralWidget(container)

    def browse_video(self):
        file_dialog = QFileDialog()
        file_path, _ = file_dialog.getOpenFileName(self, "选择视频文件", "", "视频文件 (*.mp4 *.avi *.mov)")
        if file_path:
            self.video_path_label.setText(f"视频路径: {file_path}")
            self.video_path = file_path

    def browse_output_folder(self):
        folder_dialog = QFileDialog()
        folder_path = folder_dialog.getExistingDirectory(self, "选择输出文件夹")
        if folder_path:
            self.output_folder_label.setText(f"输出文件夹: {folder_path}")
            self.output_folder = folder_path

    def split_video(self):
        try:
            # Get user input values
            video_path = getattr(self, 'video_path', None)
            if not video_path:
                QMessageBox.warning(self, "警告", "请选择一个视频文件！")
                return

            num_parts = self.parts_input.text()
            if not num_parts.isdigit() or int(num_parts) <= 0:
                QMessageBox.warning(self, "警告", "请输入有效的分割部分数量！")
                return
            num_parts = int(num_parts)

            audio_threshold = self.threshold_input.text()
            audio_threshold = float(audio_threshold) if audio_threshold else -35.0

            prefix = self.prefix_input.text()
            if not prefix:
                QMessageBox.warning(self, "警告", "请输入文件名前缀！")
                return

            output_folder = getattr(self, 'output_folder', None)
            if not output_folder:
                QMessageBox.warning(self, "警告", "请选择输出文件夹！")
                return

            # Export audio to a temporary file
            temp_audio_path = tempfile.mktemp(suffix=".wav")
            subprocess.run(["ffmpeg", "-y", "-i", video_path, "-q:a", "0", "-map", "a", temp_audio_path], check=True)

            # Load audio using pydub for analysis
            audio_segment = AudioSegment.from_wav(temp_audio_path)
            audio_volume = [segment.dBFS for segment in audio_segment[::1000]]

            # Determine split points based on audio volume
            split_points = [0]
            for i in range(1, len(audio_volume)):
                if audio_volume[i] < audio_threshold and len(split_points) < num_parts:
                    split_points.append(i / 1000.0)
            split_points.append(audio_segment.duration_seconds)

            # Ensure we have the correct number of parts
            if len(split_points) > num_parts + 1:
                split_points = split_points[:num_parts + 1]
            elif len(split_points) < num_parts + 1:
                extra_splits = num_parts + 1 - len(split_points)
                for i in range(extra_splits):
                    split_points.insert(-1, split_points[-2] + (split_points[-1] - split_points[-2]) / (extra_splits + 1))

            # Split video based on split points using ffmpeg to avoid re-encoding
            for idx in range(len(split_points) - 1):
                start = split_points[idx]
                end = split_points[idx + 1]
                output_path = os.path.join(output_folder, f"{prefix}_{idx + 1:02d}.mp4")
                subprocess.run([
                    "ffmpeg", "-y", "-ss", str(start), "-i", video_path, "-to", str(end - start), "-c", "copy", output_path
                ], check=True)

            QMessageBox.information(self, "成功", f"视频已成功分割为 {num_parts} 个部分！")
        except Exception as e:
            print(f"发生错误: {str(e)}")
            import traceback
            traceback.print_exc()
            QMessageBox.critical(self, "错误", f"发生错误: {str(e)}\n请查看终端以获取更多详细信息。")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = VideoSplitterApp()
    window.show()
    sys.exit(app.exec_())