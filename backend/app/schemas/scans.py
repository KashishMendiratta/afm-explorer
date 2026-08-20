from pydantic import BaseModel


class ScanMetaOut(BaseModel):
    i_length: int | None
    j_length: int | None
    spring_constant: float | None
    sensitivity: float | None
    columns: list[str]
    units: list[str]


class ScanSummary(BaseModel):
    scan_id: str
    m: int
    n: int
    n_series: int
    source_filename: str
    meta: ScanMetaOut


class ScanUploadResponse(BaseModel):
    scan_id: str
    m: int
    n: int
    n_series: int
    n_curves: int


class HeatmapResponse(BaseModel):
    scan_id: str
    series: int
    kind: str  # "height" | "stiffness"
    method: str | None = None
    m: int
    n: int
    values: list[list[float | None]]
