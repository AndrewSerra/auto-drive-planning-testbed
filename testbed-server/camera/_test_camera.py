
if __name__ == "__main__":
    import cv2 as cv

    cam = cv.VideoCapture(0)

    while True:
        ret, frame = cam.read()

        cv.imshow("Webcam", frame)
        if cv.waitKey(1) & 0xFF == ord('q'): break

    cam.release()
    cv.destroyAllWindows()
        
        