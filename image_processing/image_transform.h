#ifndef IMAGE_TRANSFORM_H
#define IMAGE_TRANSFORM_H

#include <iostream>
#include <opencv2/core.hpp>
#include <opencv2/opencv.hpp>
#include "image_processor.h"


#define BOTTOM_LEFT_TAG_ID    0
#define TOP_RIGHT_TAG_ID      1


namespace image_transform {

    enum AprilTagCornerIndex {
        TOP_LEFT,
        TOP_RIGHT,
        BOTTOM_RIGHT,
        BOTTOM_LEFT
    };

    class ImageTransform : public ImageProcessor {

        private:
        std::string imagePath_;
        cv::aruco::ArucoDetector detector_;
        cv::Mat transformMatrix_;
        cv::Scalar cornerColor_ = cv::Scalar(0, 255, 0);
        int thickness_ = 8;

        static cv::aruco::ArucoDetector configureDetector();
        static cv::Vec3f toLine(cv::Point2f a, cv::Point2f b);
        static cv::Point2f intersect(cv::Vec3f l1, cv::Vec3f l2);
        void drawAprilTagDetections(cv::Mat img, int markerId, std::vector<cv::Point2f> markerCorners);

        public:
        ImageTransform(const std::string& imagePath);
        ImageTransform(cv::Mat image);
        ~ImageTransform();

        cv::Mat projectImage(cv::Mat image);
        void saveImage(cv::Mat image, std::string outputFilePath) override;
    };

} // namespace image_transform

#endif
