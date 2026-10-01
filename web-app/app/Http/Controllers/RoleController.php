<?php

namespace App\Http\Controllers;

use App\Models\Role;
use Illuminate\Http\Request;

class RoleController extends Controller
{
    public function __construct()
    {
        $this->middleware('auth');
    }

    public function index()
    {
        $this->authorize('viewAny', Role::class);

        $roles = Role::all();

        return view('roles.index', compact('roles'));
    }

    public function create()
    {
        $this->authorize('create', Role::class);

        return view('roles.create');
    }

    public function store(Request $request)
    {
        $this->authorize('create', Role::class);

        Role::create($request->validate(['roleName' => ['required', 'string', 'max:255']]));

        return redirect()->route('roles.index')
            ->with('Success', 'Role created successfully.');
    }

    public function edit(Role $role)
    {
        $this->authorize('update', $role);

        return view('roles.edit', compact('role'));
    }

    public function update(Request $request, Role $role)
    {
        $this->authorize('update', $role);

        $role->update($request->validate(['roleName' => ['required', 'string', 'max:255']]));

        return redirect()->route('roles.index')
            ->with('Success', 'Role updated successfully');
    }

    public function destroy(Role $role)
    {
        $this->authorize('delete', $role);

        $role->delete();

        return redirect()->route('roles.index')
            ->with('Success', 'Role deleted successfully');
    }
}
