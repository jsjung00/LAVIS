import zarr
import json
from typing import List

class SABERMask:

    def __init__(self, run_name: str, mask_name: str, zarr_store):
        """Initialize the mask with its run name and the Zarr store."""
        self.run_name = run_name
        self.mask_name = mask_name
        self.zarr_store = zarr_store

    @property
    def mask_array(self):
        """Return the mask array for this run."""
        return self.zarr_store[self.run_name]['masks'][self.mask_name]['mask']

    @property
    def area(self) -> int:
        meta = self.zarr_store[self.run_name]['masks'][self.mask_name].attrs
        return meta['area']

    @property
    def bbox(self) -> List[int]:
        """Return the bounding box of the mask."""
        meta = self.zarr_store[self.run_name]['masks'][self.mask_name].attrs
        return meta['bbox']

    @property
    def description(self) -> str:
        """Return the description of the mask."""
        meta = self.zarr_store[self.run_name]['masks'][self.mask_name].attrs
        return meta['description']

    @property
    def hashtags(self) -> List[str]:
        """Return the hashtags associated with the mask."""
        meta = self.zarr_store[self.run_name]['masks'][self.mask_name].attrs
        return json.loads(meta['hashtags'])

    @property
    def original_segmentation_id(self) -> int:
        """Return the original segmentation ID of the mask."""
        meta = self.zarr_store[self.run_name]['masks'][self.mask_name].attrs
        return meta['original_segmentation_id']

    @property
    def segmentation_id(self) -> int:
        """Return the segmentation ID of the mask."""
        meta = self.zarr_store[self.run_name]['masks'][self.mask_name].attrs
        return meta['segmentation_id']


class SABERRun:
    def __init__(self, run_name: str, zarr_store):
        """Initialize the run with its name and the Zarr store."""
        self.run_name = run_name
        self.zarr_store = zarr_store
        # self.metadata = json.loads(self.zarr_store[self.run_name].attrs["text_annotations"])

    @property
    def masks(self):
        """Return a list of SABERMask objects for this run."""
        mask_names = list(self.zarr_store[self.run_name]['masks'].group_keys())
        return [SABERMask(self.run_name, mask_name, self.zarr_store) for mask_name in mask_names]

    def get_mask(self, mask_name: str) -> SABERMask:
        """Get a specific mask by its name."""
        if mask_name not in self.masks:
            raise ValueError(f"Mask '{mask_name}' does not exist in the run '{self.run_name}'.")
        return SABERMask(self.run_name, mask_name, self.zarr_store)

    @property
    def image_array(self):
        """Return the image array for this run."""
        return self.zarr_store[self.run_name]['image']


class SABERZarr:

    def __init__(self, root_path: str):
        """Initialize the Zarr reader with the root path."""
        self.root_path = root_path
        self.zarr_store = zarr.open(root_path, mode='r')

    @property
    def runs(self):
        run_names = [key for key in self.zarr_store.group_keys() if "masks" in self.zarr_store[key].group_keys()]
        return [SABERRun(run_name, self.zarr_store) for run_name in run_names]

    def get_run(self, run_name: str) -> SABERRun:
        """Get a specific run by its name."""
        if run_name not in self.runs:
            raise ValueError(f"Run '{run_name}' does not exist in the Zarr store.")
        return SABERRun(run_name, self.zarr_store)