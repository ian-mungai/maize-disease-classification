<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Model;

class Disease extends Model
{
    public const NAMES = ['Blight', 'Common Rust', 'Gray Leaf Spot', 'Healthy'];

    protected $primaryKey = 'diseaseId';

    protected $fillable = [
        'diseaseName',
        'recommendation',
    ];
}
