<?php

namespace App\Http\Controllers;

use App\Models\Disease;
use Illuminate\Http\Request;
use Illuminate\Validation\Rule;

class DiseaseController extends Controller
{
    public function __construct()
    {
        $this->middleware('auth');
    }

    public function index()
    {
        $this->authorize('viewAny', Disease::class);

        $diseases = Disease::orderBy('diseaseName')->get();

        return view('diseases.index', compact('diseases'));
    }

    public function create()
    {
        $this->authorize('create', Disease::class);

        return view('diseases.create', ['names' => Disease::NAMES]);
    }

    public function store(Request $request)
    {
        $this->authorize('create', Disease::class);

        Disease::create($this->validated($request));

        return redirect()->route('diseases.index')
            ->with('Success', 'Disease created successfully.');
    }

    public function edit(Disease $disease)
    {
        $this->authorize('update', $disease);

        return view('diseases.edit', ['disease' => $disease, 'names' => Disease::NAMES]);
    }

    public function update(Request $request, Disease $disease)
    {
        $this->authorize('update', $disease);

        $disease->update($this->validated($request, $disease));

        return redirect()->route('diseases.index')
            ->with('Success', 'Disease updated successfully');
    }

    public function destroy(Disease $disease)
    {
        $this->authorize('delete', $disease);

        $disease->delete();

        return redirect()->route('diseases.index')
            ->with('Success', 'Disease deleted successfully');
    }

    /**
     * Each class the model predicts has at most one recommendation.
     */
    private function validated(Request $request, ?Disease $disease = null): array
    {
        return $request->validate([
            'diseaseName' => [
                'required',
                Rule::in(Disease::NAMES),
                Rule::unique('diseases', 'diseaseName')->ignore($disease?->diseaseId, 'diseaseId'),
            ],
            'recommendation' => ['required', 'string', 'max:10000'],
        ]);
    }
}
