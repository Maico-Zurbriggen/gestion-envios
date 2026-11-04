
from pydantic import BaseModel, ConfigDict


class ApiModel(BaseModel):
    """Modelo base para contratos Pydantic v2."""
    model_config = ConfigDict(populate_by_name=True)



