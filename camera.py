import cv2

# camera 테스트

def test_video_devices():
    for i in range(38):  # /dev/video0 부터 /dev/video37 까지 시도
        cap = cv2.VideoCapture(i)
        if cap.isOpened():
            print(f"Device /dev/video{i} opened successfully.")
            ret, frame = cap.read()
            if ret:
                cv2.imshow(f"Video device {i}", frame)
                cv2.waitKey(1000)  # 1초 동안 프레임을 표시
                cv2.destroyAllWindows()
            else:
                print(f"Device /dev/video{i} could not read frame.")
            cap.release()
        else:
            print(f"Device /dev/video{i} could not be opened.")
    cv2.destroyAllWindows()

test_video_devices()
