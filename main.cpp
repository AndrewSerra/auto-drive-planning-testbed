#include "image_transform.h"
#include "boundary_detection.h"
#include <iostream>
#include <stdexcept>

int main(int argc, char* argv[]) {
    if (argc < 3) {
        std::cerr << "Usage: " << argv[0] << " <input_image> <output_path>" << std::endl;
        return 1;
    }

    std::string inputPath = argv[1];
    std::string outputPath = argv[2];

    try {
        image_transform::ImageTransform transform(inputPath);
        transform.saveImage({}, outputPath + "projection.jpg");
        image_transform::BoundaryDetection boundary(outputPath + "projection.jpg");
        cv::Mat projection = cv::imread(outputPath + "projection.jpg");
        boundary.saveImage(projection, outputPath + "boundary.jpg");
    } catch (const std::out_of_range& e) {
        std::cerr << "Out of range error: " << e.what() << std::endl;
        std::cerr << "AprilTag markers may not have been detected in the image." << std::endl;
        return 1;
    } catch (const std::runtime_error& e) {
        std::cerr << "Runtime error: " << e.what() << std::endl;
        return 1;
    } catch (const std::exception& e) {
        std::cerr << "Error: " << e.what() << std::endl;
        return 1;
    }

    return 0;
}
