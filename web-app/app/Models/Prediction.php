<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Model;
use Illuminate\Database\Eloquent\Relations\BelongsTo;

class Prediction extends Model
{
    protected $primaryKey = 'predictionId';

    protected $fillable = [
        'description',
        'imageName',
        'imageHash',
        'prediction',
    ];

    public function user(): BelongsTo
    {
        return $this->belongsTo(User::class, 'userId', 'userId');
    }

    public function disease(): BelongsTo
    {
        return $this->belongsTo(Disease::class, 'prediction', 'diseaseName');
    }
}
