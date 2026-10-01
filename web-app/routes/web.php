<?php

use Illuminate\Support\Facades\Route;

Auth::routes();

Route::resource('diseases', DiseaseController::class);
Route::resource('roles', RoleController::class);
Route::resource('predictions', PredictionController::class);
Route::get('/', function () {
    return redirect(route('login'));
});


Route::get('/dashboard',function ()
{
    return view('dashboard');
});
