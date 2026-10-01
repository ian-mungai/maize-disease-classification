<?php

namespace App\Http\Controllers;

use App\Models\Disease;
use Illuminate\Http\Request;

class DiseaseController extends Controller
{
    public function __construct()
    {
        $this->middleware('auth');
    }

    public function index()
    {
        $diseases = Disease::all();

        return view('diseases.index', compact('diseases'))
            ->with('i', (request()->input('page', 1) - 1) * 5);
    }

    public function create()
    {
        return view('diseases.create');
    }

    public function store(Request $request)
    {
        $request->validate([
            'diseaseName' => 'required',
            'recommendation' => 'required',
        ]);

        Disease::create($request->all());

        return redirect()->route('diseases.index')
            ->with('Success', 'Disease created successfully.');
    }

    public function show(Disease $disease)
    {
        return view('diseases.show', compact('disease'));
    }

    public function edit(Disease $disease)
    {
        return view('diseases.edit', compact('disease'));
    }

    public function update(Request $request, Disease $disease)
    {
        $request->validate([
            'diseaseName' => 'required',
            'recommendation' => 'required',
        ]);

        $disease->update($request->all());

        return redirect()->route('diseases.index')
            ->with('Success', 'Disease updated successfully');
    }

    public function destroy(Disease $disease)
    {
        $disease->delete();

        return redirect()->route('diseases.index')
            ->with('Success', 'Disease deleted successfully');
    }
}
