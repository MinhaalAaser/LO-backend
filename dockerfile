# Use an official Python runtime as a parent image
FROM python:3.12.4-slim-bookworm

# Set the working directory in the container
WORKDIR /app

# Copy the current directory contents into the container at /app
COPY . /app

# Install any needed packages specified in requirements.txt
RUN pip install pipenv
RUN pipenv install

# Expose the port on which your Flask app will run
EXPOSE 5000

# Define environment variables (optional)
ENV FLASK_APP=app.py
ENV FLASK_RUN_HOST=0.0.0.0

# Run Gunicorn
CMD ["pipenv", "run", "gunicorn", "--bind", "0.0.0.0:5000", "app:app"]
