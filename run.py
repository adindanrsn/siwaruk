from app import create_app

app = create_app()

if __name__ == "__main__":
    print("Flask akan dijalankan")
    app.run(debug=True)