from r2d2_backend import create_app


app = create_app()


if __name__ == "__main__":
    app.run(
        host=app.config.get("HOST", "127.0.0.1"),
        port=int(app.config.get("PORT", 5000)),
        debug=bool(app.config.get("DEBUG", False)),
    )
