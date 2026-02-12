#ifndef BOUNDARY_DETECTION_H
#define BOUNDARY_DETECTION_H

#include <opencv2/core.hpp>
#include <opencv2/opencv.hpp>
#include "image_processor.h"

namespace image_transform {

    class BoundaryDetection : public ImageProcessor {

        private:
        std::string imagePath_;
        cv::Scalar boundaryColorHigh_ = cv::Scalar(114, 255, 255);
        cv::Scalar boundaryColorLow_ = cv::Scalar(40, 180, 190);

        public:
        BoundaryDetection(const std::string& imagePath);
        ~BoundaryDetection();
        cv::Mat getBoundary(cv::Mat image);
        cv::Mat getBoundary(const std::string& imagePath);
        void saveImage(cv::Mat image, std::string outputFilePath) override;
    };
}

#endif
