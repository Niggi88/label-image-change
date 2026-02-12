from pathlib import Path
import filecmp
from yolo_utils.yolo_paths_split import YoloPathsSplit
from pprint import pprint
import pandas as pd


original_data = Path("/media/sarah/OS/snapshot_change_detection/data_validation/dataset/original_data")
testcase_data = Path("/media/sarah/OS/snapshot_change_detection/data_validation/dataset/testcase_data_faulty")


# match, mismatch, errors = filecmp.cmpfiles(original_data, testcase_data, common)

from pathlib import Path
import filecmp


def compare_label_dirs(dir1: Path, dir2: Path, split: str):
    labels1 = dir1 / split / "labels"
    labels2 = dir2 / split / "labels"

    files1 = sorted(f.name for f in labels1.glob("*.txt"))
    files2 = sorted(f.name for f in labels2.glob("*.txt"))



    match, mismatch, errors = filecmp.cmpfiles(
        labels1,
        labels2,
        files1,
        shallow=False
    )

    if mismatch or errors:
        if mismatch:
            print(f"\mismatch in {split}: {mismatch}")
        if errors:
            print(f"\nerrors in {split}: {errors}")
        return mismatch

    print(f"{split} identical.")
    return []


def compare_all_datasets(original_root: Path, testcase_root: Path):
    faults_df = []
    original_datasets = sorted(d.name for d in original_root.iterdir() if d.is_dir())
    print(original_datasets)
    for dataset in original_datasets:

        dir1 = original_root / dataset
        dir2 = testcase_root / dataset

        # train
        labels1_train = dir1 / "train" / "labels"
        labels2_train = dir2 / "train" / "labels"
        mismatch_train = compare_label_dirs(dir1, dir2, "train")
        print(f"\ncompare {dir1} with {dir2}")

        if mismatch_train:
            print(f"-- check train for {dir1}")
            faults_df = check_whats_wrong(mismatch_train, labels1_train, labels2_train, faults_df)
        # val
        labels1_val = dir1 / "val" / "labels"
        labels2_val = dir2 / "val" / "labels"
        mismatch_val = compare_label_dirs(dir1, dir2, "val")
        print(f"\ncompare {dir1} with {dir2}")
        if mismatch_val:
            print(f"-- check val for {dir1}")
            faults_df = check_whats_wrong(mismatch_val, labels1_val, labels2_val, faults_df)

    return pd.DataFrame(faults_df)
        


def check_whats_wrong(mismatch, labels1: Path, labels2: Path, rows):
    if not mismatch:
        return

    for filename in mismatch:
        file1 = labels1 / filename
        file2 = labels2 / filename

        print(f"\n===== {filename} =====")

        if not file1.exists():
            print(f"{file1} missing in original")
            continue

        if not file2.exists():
            print(f"{file2} missing in testcase")
            continue

        text1 = file1.read_text().splitlines()
        text2 = file2.read_text().splitlines()

        rows.append({
            "file_original": str(Path(*file1.parts[-5:])),
            "file_testcase": str(Path(*file2.parts[-5:])),
            "original": text1,
            "testcase": text2,
        })

        # print(f"original: {text1}")
        # print(f"testcase: {text2}")

    return rows
    
if __name__ == "__main__":

    original_data = Path("/media/sarah/OS/snapshot_change_detection/data_validation/dataset/original_data")
    testcase_data = Path("/media/sarah/OS/snapshot_change_detection/data_validation/dataset/testcase_data_faulty")

    faults_df = compare_all_datasets(original_data, testcase_data)

    # string machen, sonst: TypeError: unhashable type: 'list'
    faults_df["original"] = faults_df["original"].apply(lambda x: "\n".join(x))
    faults_df["testcase"] = faults_df["testcase"].apply(lambda x: "\n".join(x))
    summary = (
        faults_df
        .groupby(["original", "testcase"])
        .size()
        .reset_index(name="count")
        .sort_values("count", ascending=False)
    )

    print(summary)