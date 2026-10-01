# Maize Disease Classification Web App

The Laravel 13 interface of the maize disease classifier: users upload a leaf image, the Flask service in [`../flask-app`](../flask-app) predicts its class and the app stores the result with an admin-edited recommendation.

## Install

Requires PHP 8.3 or newer (verified with 8.5.11), Composer 2 and a MySQL 8 or newer database. The full setup, including the database and the Flask service, is in the [root README](../README.md#install). From this folder:

```bash
composer install
cp .env.example .env
php artisan key:generate
php artisan migrate --seed
```

Set the database name, user and password in `.env`. [`.env.example`](.env.example) lists every setting with placeholders.

## Usage

Start the Flask service first, then run the app on the loopback interface:

```bash
php artisan serve --host=127.0.0.1 --port=8000
```

Register at `http://127.0.0.1:8000`, then give your account the administrator role:

```bash
php artisan app:make-admin <EMAIL>
```

Routes, access rules and the end-to-end check are described in the [root README](../README.md#usage).

## Contributing

Individual project; contributions are not accepted.

## License

The project code is licensed under the [MIT License](../LICENSE). Third-party packages keep their own licenses, recorded in `composer.lock` and `package-lock.json`.
