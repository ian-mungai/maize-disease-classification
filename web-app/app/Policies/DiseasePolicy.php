<?php

namespace App\Policies;

use App\Models\Disease;
use App\Models\User;

/**
 * Only administrators manage disease recommendations.
 */
class DiseasePolicy
{
    public function viewAny(User $user): bool
    {
        return $user->isAdmin();
    }

    public function create(User $user): bool
    {
        return $user->isAdmin();
    }

    public function update(User $user, Disease $model): bool
    {
        return $user->isAdmin();
    }

    public function delete(User $user, Disease $model): bool
    {
        return $user->isAdmin();
    }
}
