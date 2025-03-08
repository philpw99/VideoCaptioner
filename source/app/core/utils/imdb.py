from imdb import Cinemagoer, IMDbError

def get_movie_info(id: str, topActors = 10):
    if id[:2].lower() == "tt":
        id = id[2:]
    if not id.isdigit():
        return None, None, None
    try:
        # Create the cinema class
        ia = Cinemagoer()
        
        # Get movie
        movie = ia.get_movie(id)
        if not movie:
            return None, None, None
        
        cast = movie["cast"]
        if len(cast) > topActors:
            cast = cast[:topActors]    # Limit the actor list length.

        if "Documentary" in movie["genres"]:
            # Documentary use real names as actors.
            actors = ", ".join(str(actor) for actor in cast)
        else:
            actors = ", ".join(str(actor.currentRole) for actor in cast)
        
        plot = movie.get("plot outline")
        if not plot:
            plot = movie.get("plot")
            if type(plot) == type(list()):
                plot = plot[0]
        
        genres = " and ".join(movie["genres"])
        
        movie_info=f"This is a {movie["year"]} {genres} {movie["kind"]}.\n" \
            + "Plot summary:\n" \
            + f"{plot}\n" \
            + f"characters: {actors}"
        # Return movie info and cover.
        return movie_info, movie["cover url"], movie["kind"]
        
    except IMDbError as e:
        print(f"Error in IMDB: {e}")
        