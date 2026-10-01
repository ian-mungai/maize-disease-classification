<?php

namespace Database\Seeders;

use App\Models\Role;
use Illuminate\Database\Seeder;

class RoleSeeder extends Seeder
{
    /**
     * Seed the two role names. Safe to run repeatedly.
     */
    public function run(): void
    {
        foreach (['Admin', 'NormalUser'] as $roleName) {
            Role::firstOrCreate(['roleName' => $roleName]);
        }
    }
}
