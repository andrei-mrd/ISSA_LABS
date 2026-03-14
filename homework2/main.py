import cv2
import numpy as np

cam = cv2.VideoCapture('Lane_Detection_Test_Video_01.mp4')

while True:
    ret, frame = cam.read()

    if not ret:
        break

    height, width = frame.shape[:2]
    frame = cv2.resize(frame, (width//3, height//3))

    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

    h, w = gray.shape

    upper_left = (int(w * 0.46), int(h * 0.75))
    upper_right = (int(w * 0.54), int(h * 0.75))
    lower_left = (int(w * 0.05), h)
    lower_right = (int(w * 0.95), h)

    points = np.array([upper_left, upper_right, lower_right, lower_left], dtype=np.int32)

    mask = np.zeros(gray.shape, dtype=np.uint8)

    cv2.fillConvexPoly(mask, points, 255)

    road = cv2.bitwise_and(gray, mask)

    trapezoid_bounds = np.array([
        upper_right,
        upper_left,
        lower_left,
        lower_right
    ], dtype=np.float32)

    frame_bounds = np.array([
        (w, 0),
        (0, 0),
        (0, h),
        (w, h)
    ], dtype=np.float32)

    M = cv2.getPerspectiveTransform(trapezoid_bounds, frame_bounds)

    top_down = cv2.warpPerspective(road, M, (w, h))

    blur = cv2.blur(top_down, (5, 5))

    cv2.imshow("Top Down", top_down)
    cv2.imshow("Blur", blur)
    cv2.imshow("Grayscale", gray)
    cv2.imshow("Trapezoid", mask)
    cv2.imshow("Road", road)

    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cam.release()
cv2.destroyAllWindows()