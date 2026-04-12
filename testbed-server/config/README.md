# Testbed Configuration File

This file allows the testbed to be configured with specific values that determine the operation and transformations done within the system. Each section will explain how each field will effect the runtime.

**Note**: The config file should be located in the root of the project not in this directory.

## Dimensions

Creates a mapping between actual field size to image shape. The image size will be the birds-eye view image size generated.

Units:
- `field`: centimeters
- `image`: pixels

`TestbedConfig` class will have transformation functions available to use. 

## Grid

Determines how many sections the field should be divided in. This allows control the granularity of the control of robots. Higher means more precision.

The grid also allows a mental mapping between the physical field and the image the system uses for control.

Takes integer values.