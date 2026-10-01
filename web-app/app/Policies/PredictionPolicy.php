<?php

namespace App\Policies;

use App\Models\Prediction;
use App\Models\User;

/**
 * Users see only their own predictions.
 */
class PredictionPolicy
{
    public function viewAny(User $user): bool
    {
        return true;
    }

    public function create(User $user): bool
    {
        return true;
    }

    public function view(User $user, Prediction $prediction): bool
    {
        return $prediction->userId === $user->userId;
    }
}
