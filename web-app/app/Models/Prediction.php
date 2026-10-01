<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Factories\HasFactory;
use Illuminate\Database\Eloquent\Model;

class Prediction extends Model
{
    use HasFactory;
    protected $primaryKey = 'predictionId';

    public function user()
    {
        return $this->belongsTo(User::class);
    }

}
