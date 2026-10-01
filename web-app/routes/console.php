<?php

use App\Models\User;
use Illuminate\Support\Facades\Artisan;

Artisan::command('app:make-admin {email}', function (string $email) {
    $user = User::where('email', $email)->first();
    if (! $user) {
        $this->error("No registered user has the email {$email}.");

        return 1;
    }

    $user->role = User::ROLE_ADMIN;
    $user->save();
    $this->info("{$email} is an administrator.");

    return 0;
})->purpose('Give a registered user the administrator role');
