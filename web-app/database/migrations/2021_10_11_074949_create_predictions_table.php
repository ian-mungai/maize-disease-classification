<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\Schema;

class CreatePredictionsTable extends Migration
{
    public function up()
    {
        Schema::create('predictions', function (Blueprint $table) {
            $table->increments('predictionId');
            $table->string('description');
            $table->string('imageName');
            $table->integer('userId')->unsigned();
            $table->string('prediction');
            $table->foreign('userId')->references('userId')->on('users')->onDelete('cascade');
            $table->timestamps();
        });
    }

    public function down()
    {
        Schema::dropIfExists('predictions');
    }
}
