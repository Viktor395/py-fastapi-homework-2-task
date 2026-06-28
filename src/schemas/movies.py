from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import date

class GenreSchema(BaseModel):
    id: int
    name: str
    class Config:
        from_attributes = True

class ActorSchema(BaseModel):
    id: int
    name: str
    class Config:
        from_attributes = True

class CountrySchema(BaseModel):
    id: int
    code: str
    name: Optional[str] = None
    class Config:
        from_attributes = True

class MovieListItemSchema(BaseModel):
    id: int
    name: str
    date: date
    score: float
    overview: str
    
    class Config:
        from_attributes = True

class MovieBase(BaseModel):
    name: str = Field(..., max_length=255)
    date: date
    score: float = Field(..., ge=0, le=100)
    overview: str
    status: str
    budget: float = Field(..., ge=0)
    revenue: float = Field(..., ge=0)

class MovieCreate(MovieBase):
    country: str
    genres: List[str]
    actors: List[str]
    languages: List[str]

class MovieResponse(MovieBase):
    id: int
    country: CountrySchema
    genres: List[GenreSchema]
    actors: List[ActorSchema]
    languages: List[GenreSchema]
    class Config:
        from_attributes = True

class MovieUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=255)
    date: Optional[date] = None
    score: Optional[float] = Field(None, ge=0, le=100)
    overview: Optional[str] = None
    status: Optional[str] = None
    budget: Optional[float] = Field(None, ge=0)
    revenue: Optional[float] = Field(None, ge=0)

class MovieListResponseSchema(BaseModel):
    movies: List[MovieListItemSchema]
    prev_page: Optional[str] = None
    next_page: Optional[str] = None
    total_pages: int
    total_items: int

    class Config:
        from_attributes = True