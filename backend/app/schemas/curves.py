from pydantic import BaseModel


class CurveCoordinateOut(BaseModel):
    series: int
    i: int
    j: int
    n_points: int


class CurveOut(BaseModel):
    scan_id: str
    series: int
    i: int
    j: int
    distance: list[float]
    force: list[float]


class FitResultOut(BaseModel):
    scan_id: str
    series: int
    i: int
    j: int
    method: str
    slope: float
    intercept: float
    start_index: int
    end_index: int
    contact_index: int
    r_squared: float
