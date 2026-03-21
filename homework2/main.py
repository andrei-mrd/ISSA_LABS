import cv2
import numpy as np

cam = cv2.VideoCapture('Lane_Detection_Test_Video_01.mp4')

cv2.namedWindow("Top Down", cv2.WINDOW_NORMAL)
cv2.namedWindow("Blur", cv2.WINDOW_NORMAL)
cv2.namedWindow("Grayscale", cv2.WINDOW_NORMAL)
cv2.namedWindow("Trapezoid", cv2.WINDOW_NORMAL)
cv2.namedWindow("Road", cv2.WINDOW_NORMAL)
cv2.namedWindow("Binarised", cv2.WINDOW_NORMAL)
cv2.namedWindow("Lines", cv2.WINDOW_NORMAL)
cv2.namedWindow("Final", cv2.WINDOW_NORMAL)

cv2.resizeWindow("Top Down", 420, 230)
cv2.resizeWindow("Blur", 420, 230)
cv2.resizeWindow("Grayscale", 420, 230)
cv2.resizeWindow("Trapezoid", 420, 230)
cv2.resizeWindow("Road", 420, 230)
cv2.resizeWindow("Binarised", 420, 230)
cv2.resizeWindow("Lines", 420, 230)
cv2.resizeWindow("Final", 420, 230)

cv2.moveWindow("Top Down", 20, 40)
cv2.moveWindow("Blur", 460, 40)
cv2.moveWindow("Grayscale", 900, 40)
cv2.moveWindow("Trapezoid", 1340, 40)
cv2.moveWindow("Road", 20, 320)
cv2.moveWindow("Binarised", 460, 320)
cv2.moveWindow("Lines", 900, 320)
cv2.moveWindow("Final", 1340, 320)

sobel_vertical = np.float32([
    [-1, -2, -1],
    [ 0,  0,  0],
    [ 1,  2,  1]
])

sobel_horizontal = np.transpose(sobel_vertical)

left_top = (0, 0)
left_bottom = (0, 0)
right_top = (0, 0)
right_bottom = (0, 0)

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

    blur = cv2.GaussianBlur(top_down, (5, 5), 0)

    blur_float = np.float32(blur)

    sobel_v = cv2.filter2D(blur_float, -1, sobel_vertical)
    sobel_h = cv2.filter2D(blur_float, -1, sobel_horizontal)

    sobel_combined = np.sqrt(sobel_v**2 + sobel_h**2)

    result = cv2.convertScaleAbs(sobel_combined)

    threshold = 127
    _, binarised = cv2.threshold(result, threshold, 255, cv2.THRESH_BINARY)

    cleaned = binarised.copy()

    edge_cols = int(w * 0.05)

    cleaned[:, :edge_cols] = 0
    cleaned[:, w - edge_cols:] = 0

    mid = w // 2

    left_half = cleaned[:, :mid]
    right_half = cleaned[:, mid:]

    left_points = np.argwhere(left_half == 255)
    right_points = np.argwhere(right_half == 255)

    left_ys = left_points[:, 0]
    left_xs = left_points[:, 1]

    right_ys = right_points[:, 0]
    right_xs = right_points[:, 1] + mid

    lines_frame = cv2.cvtColor(cleaned, cv2.COLOR_GRAY2BGR)

    if len(left_xs) > 1 and len(right_xs) > 1:
        left_b, left_a = np.polynomial.polynomial.polyfit(left_xs, left_ys, 1)
        right_b, right_a = np.polynomial.polynomial.polyfit(right_xs, right_ys, 1)

        left_top_y = 0
        left_bottom_y = h
        right_top_y = 0
        right_bottom_y = h

        if abs(left_a) > 1e-8:
            left_top_x = (left_top_y - left_b) / left_a
            left_bottom_x = (left_bottom_y - left_b) / left_a

            if abs(left_top_x) < 1e8 and abs(left_bottom_x) < 1e8:
                left_top = (int(left_top_x), int(left_top_y))
                left_bottom = (int(left_bottom_x), int(left_bottom_y))

        if abs(right_a) > 1e-8:
            right_top_x = (right_top_y - right_b) / right_a
            right_bottom_x = (right_bottom_y - right_b) / right_a

            if abs(right_top_x) < 1e8 and abs(right_bottom_x) < 1e8:
                right_top = (int(right_top_x), int(right_top_y))
                right_bottom = (int(right_bottom_x), int(right_bottom_y))

    cv2.line(lines_frame, left_top, left_bottom, (200, 0, 0), 5)
    cv2.line(lines_frame, right_top, right_bottom, (100, 0, 0), 5)
    cv2.line(lines_frame, (mid, 0), (mid, h), (255, 0, 0), 1)

    left_line_frame = np.zeros((h, w, 3), dtype=np.uint8)
    right_line_frame = np.zeros((h, w, 3), dtype=np.uint8)

    cv2.line(left_line_frame, left_top, left_bottom, (255, 0, 0), 3)
    cv2.line(right_line_frame, right_top, right_bottom, (255, 0, 0), 3)

    M_back = cv2.getPerspectiveTransform(frame_bounds, trapezoid_bounds)

    left_line_warped = cv2.warpPerspective(left_line_frame, M_back, (w, h))
    right_line_warped = cv2.warpPerspective(right_line_frame, M_back, (w, h))

    left_line_points = np.argwhere(left_line_warped[:, :, 0] > 0)
    right_line_points = np.argwhere(right_line_warped[:, :, 0] > 0)

    final = frame.copy()

    if len(left_line_points) > 0:
        left_line_ys = left_line_points[:, 0]
        left_line_xs = left_line_points[:, 1]
        final[left_line_ys, left_line_xs] = (50, 50, 250)

    if len(right_line_points) > 0:
        right_line_ys = right_line_points[:, 0]
        right_line_xs = right_line_points[:, 1]
        final[right_line_ys, right_line_xs] = (50, 250, 50)

    cv2.imshow("Top Down", top_down)
    cv2.imshow("Blur", blur)
    cv2.imshow("Grayscale", gray)
    cv2.imshow("Trapezoid", mask)
    cv2.imshow("Road", road)
    cv2.imshow("Binarised", binarised)
    cv2.imshow("Lines", lines_frame)
    cv2.imshow("Final", final)

    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cam.release()
cv2.destroyAllWindows()