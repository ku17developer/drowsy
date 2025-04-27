import cv2
import dlib
import serial
from scipy.spatial import distance
import time
from twilio.rest import Client
import tkinter as tk
from tkinter import ttk
from ttkthemes import ThemedStyle
import pyttsx3
import threading
import logging
import traceback

# 전역 변수 설정
phone_number = None
phone_entry = None
root = None
DROWSY_THRESHOLD = 2  # 졸음 감지 시간 임계값 (초)
EAR_THRESHOLD = 0.3   # 눈 깜빡임 비율(EAR) 임계값

# 로깅 설정
logging.basicConfig(filename='drowsy_detection.log', level=logging.INFO, format='%(asctime)s:%(levelname)s:%(message)s')

def calculate_EAR(eye):
    """
    눈 깜빡임 비율(EAR)을 계산하는 함수
    """
    A = distance.euclidean(eye[1], eye[5])
    B = distance.euclidean(eye[2], eye[4])
    C = distance.euclidean(eye[0], eye[3])
    ear_aspect_ratio = (A + B) / (2.0 * C)
    return ear_aspect_ratio

# Twilio API 설정
twilio_account_sid = '비'
twilio_auth_token = '밀'
twilio_phone_number = '입니다~'
twilio_client = Client(twilio_account_sid, twilio_auth_token)

def send_warning_message(phone_number):
    """
    경고 문자를 보내는 함수
    """
    try:
        message = twilio_client.messages.create(
            body="경고! 졸음운전 상태입니다!",
            from_=twilio_phone_number,
            to=phone_number
        )
        logging.info(f"문자 메시지가 전송되었습니다. SID: {message.sid}")
    except Exception as e:
        logging.error("문자 메시지 전송 중 오류 발생:", exc_info=True)
        print("문자 메시지 전송 중 오류 발생:", e)
        traceback.print_exc()

def play_warning_message():
    """
    음성 경고 메시지를 재생하는 함수
    """
    try:
        engine.say("경고! 졸음운전 상태입니다!")
        engine.runAndWait()
    except Exception as e:
        logging.error("음성 경고 중 오류 발생:", exc_info=True)
        print("음성 경고 중 오류 발생:", e)
        traceback.print_exc()

def create_interface():
    """
    사용자 인터페이스를 생성하는 함수
    """
    global phone_entry, root
    root = tk.Tk()
    root.title("Drowsy Driving Detection")
    root.geometry("800x400")
    style = ThemedStyle(root)
    style.set_theme("arc")

    style.configure("TLabel", font=("Helvetica", 12))

    phone_label = ttk.Label(root, text="경고 문자를 받을 전화번호:")
    phone_label.pack(pady=10)

    phone_entry = ttk.Entry(root, width=30)
    phone_entry.pack(pady=5)

    start_button = ttk.Button(root, text="감지 시작", command=detect_drowsy)
    start_button.pack(pady=10)

    root.mainloop()

def detect_drowsy():
    """
    졸음운전을 감지하는 함수
    """
    try:
        global phone_number, phone_entry
        phone_number = phone_entry.get()
        if phone_number:
            start_time = None
            elapsed_time = 0  # 초기화
            last_co2_level = 0
            motor_opened = False

            while True:
                ret, frame = cap.read()
                if not ret:
                    break

                frame = cv2.resize(frame, (960, 540))  # 프레임 크기 조정
                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                faces = hog_face_detector(gray)

                for face in faces:
                    face_landmarks = dlib_facelandmark(gray, face)
                    left_eye = []
                    right_eye = []

                    for n in range(36, 42):
                        x = face_landmarks.part(n).x
                        y = face_landmarks.part(n).y
                        left_eye.append((x, y))
                        cv2.circle(frame, (x, y), 1, (0, 0, 255), -1)

                    for n in range(42, 48):
                        x = face_landmarks.part(n).x
                        y = face_landmarks.part(n).y
                        right_eye.append((x, y))
                        cv2.circle(frame, (x, y), 1, (0, 0, 255), -1)

                    left_ear = calculate_EAR(left_eye)
                    right_ear = calculate_EAR(right_eye)
                    ear = (left_ear + right_ear) / 2
                    ear = round(ear, 2)

                    if ear < EAR_THRESHOLD:
                        if start_time is None:
                            start_time = time.time()
                        elapsed_time = time.time() - start_time

                        if elapsed_time >= DROWSY_THRESHOLD:
                            logging.info("Driver is sleeping")
                            print("Driver is sleeping")
                            threading.Thread(target=send_warning_message, args=(phone_number,)).start()
                            threading.Thread(target=play_warning_message).start()
                            threading.Thread(target=activate_buzzer).start()
                            start_time = None
                    else:
                        start_time = None
                        elapsed_time = 0

                # Display eyes closed time
                cv2.putText(frame, f"Eyes Closed: {elapsed_time:.2f}s", (20, 50), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2, cv2.LINE_AA)

                if arduino.in_waiting > 0:
                    co2_data = arduino.readline().decode().strip()
                    try:
                        co2_level = int(co2_data.split()[-1])
                        last_co2_level = co2_level
                        logging.info(f"CO2 Level: {co2_level} ppm")
                        print(f"CO2 Level: {co2_level} ppm")
                    except (ValueError, IndexError) as e:
                        logging.warning(f"Invalid CO2 data: {co2_data}")
                        print(f"Invalid CO2 data: {co2_data}")
                        co2_level = None

                    if co2_level is not None and co2_level > 2000 and not motor_opened:
                        threading.Thread(target=activate_motor).start()
                        motor_opened = True

                cv2.putText(frame, f"CO2 Level: {last_co2_level} ppm", (20, 100), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 0, 0), 2, cv2.LINE_AA)

                cv2.imshow("Are you Sleepy", frame)

                key = cv2.waitKey(30)
                if key == 27:
                    break

            cap.release()
            cv2.destroyAllWindows()
    except Exception as e:
        logging.error("감지 중 오류 발생:", exc_info=True)
        print("감지 중 오류 발생:", e)
        traceback.print_exc()

def activate_buzzer():
    """
    부저를 활성화하는 함수
    """
    try:
        arduino.write(b'B')
        time.sleep(3)
        arduino.write(b'S')
    except Exception as e:
        logging.error("부저 활성화 중 오류 발생:", exc_info=True)
        print("부저 활성화 중 오류 발생:", e)
        traceback.print_exc()

def activate_motor():
    """
    모터를 활성화하는 함수
    """
    try:
        arduino.write(b'M')
    except Exception as e:
        logging.error("모터 활성화 중 오류 발생:", exc_info=True)
        print("모터 활성화 중 오류 발생:", e)
        traceback.print_exc()

if __name__ == "__main__":
    try:
        arduino = serial.Serial('/dev/ttyACM0', 9600, timeout=1)
        time.sleep(2)
        cap = cv2.VideoCapture(0)
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 960)  # 카메라 프레임 너비 설정
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 540)  # 카메라 프레임 높이 설정
        hog_face_detector = dlib.get_frontal_face_detector()
        dlib_facelandmark = dlib.shape_predictor("shape_predictor_68_face_landmarks.dat")
        engine = pyttsx3.init()
        engine.setProperty('rate', 150)
        create_interface()
    except Exception as e:
        logging.error("초기화 중 오류 발생:", exc_info=True)
        print("초기화 중 오류 발생:", e)
        traceback.print_exc()


##아두이노 코드

#include <Wire.h>
#include <cm1106_i2c.h>
#include <Servo.h>

# CM1106 I2C 라이브러리와 서보 라이브러리 포함
# CM1106_I2C cm1106_i2c;
# Servo myServo;

#define BUZZER_PIN 8     // 부저 핀 정의
#define MOTOR_PIN 6      // 모터 핀 정의
#define CO2_THRESHOLD 2000  // CO2 임계값 정의

# bool window_opened = false;  // 창이 열렸는지 여부를 추적하는 변수

# void setup() {
#   Wire.begin();               // I2C 통신 시작
#   Serial.begin(9600);         // 시리얼 통신 시작
#   cm1106_i2c.begin();         // CM1106 센서 초기화
#   pinMode(BUZZER_PIN, OUTPUT);  // 부저 핀을 출력 모드로 설정
#   myServo.attach(MOTOR_PIN);    // 서보 모터를 모터 핀에 연결
#   myServo.write(0);             // 서보 모터 초기 위치 설정
#   delay(1000);                  // 1초 대기

#   cm1106_i2c.read_serial_number(); // 센서 일련번호 읽기
#   delay(1000);
#   cm1106_i2c.check_sw_version();   // 센서 소프트웨어 버전 확인
#   delay(1000);
# }

# void loop() {
#   uint8_t ret = cm1106_i2c.measure_result();  // CO2 측정 결과 읽기

#   if (ret == 0) {
#     // 측정이 성공했을 경우 CO2 수치 출력
#     Serial.print("Co2 : ");
#     Serial.println(cm1106_i2c.co2);

#     if (cm1106_i2c.co2 > CO2_THRESHOLD && !window_opened) {
#       // CO2 수치가 임계값을 초과하고 창이 열리지 않은 경우
#       myServo.write(180);  // 모터를 180도로 회전시켜 창을 염
#       delay(3000);         // 3초 대기
#       myServo.write(0);    // 모터를 원위치로 복귀
#       window_opened = true; // 창이 열렸음을 표시
#     }

#     delay(1000);  // 1초 대기
#   } else {
#     // 측정 실패 시 오류 메시지 출력
#     Serial.println("Failed to read from sensor!");
#   }

#   if (Serial.available() > 0) {
#     // 시리얼 데이터가 있을 경우 명령어를 읽음
#     char command = Serial.read();
#     if (command == 'B') {
#       // 'B' 명령어: 부저를 3초간 울림
#       digitalWrite(BUZZER_PIN, HIGH);
#       delay(3000);
#       digitalWrite(BUZZER_PIN, LOW);
#     } else if (command == 'S') {
#       // 'S' 명령어: 부저를 중지
#       digitalWrite(BUZZER_PIN, LOW);
#     } else if (command == 'M') {
#       // 'M' 명령어: 모터를 180도 회전 후 원위치 복귀
#       myServo.write(180);
#       delay(3000);
#       myServo.write(0);
#     }
#   }
# }
