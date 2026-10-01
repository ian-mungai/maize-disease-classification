<?php

namespace App\Policies;

use App\Models\Role;
use App\Models\User;

/**
 * Only administrators manage roles.
 */
class RolePolicy
{
    public function viewAny(User $user): bool
    {
        return $user->isAdmin();
    }

    public function create(User $user): bool
    {
        return $user->isAdmin();
    }

    public function update(User $user, Role $model): bool
    {
        return $user->isAdmin();
    }

    public function delete(User $user, Role $model): bool
    {
        return $user->isAdmin();
    }
}
