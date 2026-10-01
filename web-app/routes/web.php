<?php

use App\Http\Controllers\DiseaseController;
use App\Http\Controllers\PredictionController;
use App\Http\Controllers\RoleController;
use Illuminate\Support\Facades\Auth;
use Illuminate\Support\Facades\Route;

Auth::routes();

Route::redirect('/', '/login');

Route::middleware('auth')->group(function () {
    Route::view('/dashboard', 'dashboard')->name('dashboard');
    Route::resource('diseases', DiseaseController::class)->except('show');
    Route::resource('roles', RoleController::class)->except('show');
    Route::resource('predictions', PredictionController::class)->only(['index', 'create', 'store', 'show']);
    Route::get('predictions/{prediction}/image', [PredictionController::class, 'image'])->name('predictions.image');
});
