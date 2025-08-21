import json 
from collections import Counter 
from pathlib import Path 

def rebalance_json(json_file):
    with open(json_file, 'r') as fp:
        list_objs = json.load(fp)
    # count number of classes and their counts 
    class_counts = Counter()
    for obj in list_objs:
        class_counts[obj['caption']] += 1

    total_num_classes = len(class_counts)
    max_count = 2 * (len(list_objs) // total_num_classes)

    print(f"Max count per class: {max_count}")
    print(f"Total number of classes: {total_num_classes}")
    print(class_counts)

    # recount hashmap 
    class_counts = Counter()

    balanced_list = []
    for obj in list_objs:
        if class_counts[obj['caption']] < max_count:
            balanced_list.append(obj)
            class_counts[obj['caption']] += 1
    
    new_file_name = Path(json_file).with_name(Path(json_file).stem + "_balanced.json")
    with open(new_file_name, 'w') as fp:
        json.dump(balanced_list, fp, indent=4)
    
    print(f"Rebalanced to {new_file_name}")


if __name__ == "__main__":

    json_path = '/home/daniel.ji/cryoet-data-portal-pick-extract/LAVIS/.cache/lavis/cryoet/annotations/labels_train.json'
    rebalance_json(json_path)