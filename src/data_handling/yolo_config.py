import yaml


def generate_dataset_config(class_names, train_path, val_path, output_file, 
                          test_path=None, parent_path=".."):
    """
    Generate a YOLO dataset configuration file.
    
    Args:
        class_names: List of class names
        train_path: Path to training images
        val_path: Path to validation images  
        output_file: Output YAML filename
        test_path: Optional path to test images
        parent_path: Parent path reference
    """
    config = {
        'names': class_names,
        'nc': len(class_names),
        'path': parent_path,
        'train': train_path,
        'val': val_path
    }
    
    if test_path:
        config['test'] = test_path
    
    with open(output_file, 'w') as f:
        yaml.dump(config, f, default_flow_style=False, sort_keys=False)
    
    print(f"Generated {output_file}")
    return config


# Example usage
if __name__ == "__main__":
    class_names = [
        "nothing", "chaos", "item_added"
    ]
    
    generate_dataset_config(
        class_names=class_names,
        train_path="/media/fast/dataset/product_detection/multi_small2/synthetic/v1/train/images",
        val_path="/media/fast/dataset/product_detection/multi_small2/synthetic/v1/val/images",
        output_file="dataset.yaml"
    )