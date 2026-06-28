from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload
from sqlalchemy.exc import IntegrityError
from database import get_db
from database.models import MovieModel, CountryModel, GenreModel, ActorModel, LanguageModel
from schemas.movies import MovieCreate, MovieResponse, MovieUpdate, MovieListResponseSchema

router = APIRouter()

# Допоміжна функція для отримання або створення зв'язків
async def get_or_create(db: AsyncSession, model, name: str):
    res = await db.execute(select(model).filter(model.name == name))
    obj = res.scalar_one_or_none()
    if not obj:
        obj = model(name=name)
        db.add(obj)
        await db.flush()
    return obj

# 1. Список фільмів
@router.get("/movies/", response_model=MovieListResponseSchema)
async def get_movies(
    page: int = Query(1, ge=1), 
    per_page: int = Query(10, ge=1, le=20), 
    db: AsyncSession = Depends(get_db)
):
    count_query = await db.execute(select(func.count()).select_from(MovieModel))
    total_items = count_query.scalar() or 0
    total_pages = (total_items + per_page - 1) // per_page
    
    if total_items == 0:
        raise HTTPException(status_code=404, detail="No movies found.")
    if page > total_pages:
        raise HTTPException(status_code=404, detail="Page not found.")

    offset = (page - 1) * per_page
    query = select(MovieModel).order_by(MovieModel.id.desc()).offset(offset).limit(per_page)
    result = await db.execute(query)
    movies = result.scalars().all()
    
    base_url = "/theater/movies/"
    return {
        "movies": movies,
        "total_items": total_items,
        "total_pages": total_pages,
        "prev_page": f"{base_url}?page={page-1}&per_page={per_page}" if page > 1 else None,
        "next_page": f"{base_url}?page={page+1}&per_page={per_page}" if page < total_pages else None
    }

# 2. Створення
@router.post("/movies/", response_model=MovieResponse, status_code=status.HTTP_201_CREATED)
async def create_movie(movie_data: MovieCreate, db: AsyncSession = Depends(get_db)):
    # Пошук країни
    country_res = await db.execute(
        select(CountryModel).filter((CountryModel.name == movie_data.country) | (CountryModel.code == movie_data.country))
    )
    country = country_res.scalar_one_or_none()
    if not country:
        raise HTTPException(status_code=400, detail="Country not found")

    # Створення об'єкта
    new_movie = MovieModel(**movie_data.model_dump(exclude={"country", "genres", "actors", "languages"}), country_id=country.id)
    
    # Додавання зв'язків
    for name in movie_data.genres: new_movie.genres.append(await get_or_create(db, GenreModel, name))
    for name in movie_data.actors: new_movie.actors.append(await get_or_create(db, ActorModel, name))
    for name in movie_data.languages: new_movie.languages.append(await get_or_create(db, LanguageModel, name))

    db.add(new_movie)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(
            status_code=409, 
            detail=f"A movie with the name '{movie_data.name}' and release date '{movie_data.date}' already exists."
        )
    
    await db.refresh(new_movie)
    return await get_movie(new_movie.id, db)

# 3. Деталі
@router.get("/movies/{movie_id}/", response_model=MovieResponse)
async def get_movie(movie_id: int, db: AsyncSession = Depends(get_db)):
    query = select(MovieModel).options(
        selectinload(MovieModel.country), 
        selectinload(MovieModel.genres), 
        selectinload(MovieModel.actors), 
        selectinload(MovieModel.languages)
    ).filter(MovieModel.id == movie_id)
    
    result = await db.execute(query)
    movie = result.scalar_one_or_none()
    if not movie:
        raise HTTPException(status_code=404, detail="Movie with the given ID was not found.")
    return movie

# 4. Видалення
@router.delete("/movies/{movie_id}/", status_code=204)
async def delete_movie(movie_id: int, db: AsyncSession = Depends(get_db)):
    movie = await db.get(MovieModel, movie_id)
    if not movie:
        raise HTTPException(status_code=404, detail="Movie with the given ID was not found.")
    await db.delete(movie)
    await db.commit()
    return None

# 5. Оновлення
@router.patch("/movies/{movie_id}/")
async def update_movie(movie_id: int, update_data: MovieUpdate, db: AsyncSession = Depends(get_db)):
    query = select(MovieModel).options(
        selectinload(MovieModel.country), selectinload(MovieModel.genres), 
        selectinload(MovieModel.actors), selectinload(MovieModel.languages)
    ).filter(MovieModel.id == movie_id)
    
    result = await db.execute(query)
    movie = result.scalar_one_or_none()
    if not movie:
        raise HTTPException(status_code=404, detail="Movie with the given ID was not found.")
    
    for key, value in update_data.model_dump(exclude_unset=True).items():
        setattr(movie, key, value)
    
    await db.commit()
    await db.refresh(movie)
    
    movie_dict = MovieResponse.model_validate(movie).model_dump()
    return {"detail": "Movie updated successfully.", **movie_dict}
