FROM python:3.10.6
ENV PYTHONUNBUFFERED=1

WORKDIR /usr/src/app

ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

COPY requirements.txt /usr/src/app
RUN pip install -r requirements.txt

COPY . .

# Expose port for Gunicorn
EXPOSE 8000

# Start Gunicorn server
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "--timeout", "600", "project.wsgi:application"]
