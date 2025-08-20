import { NgModule } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { HydroMeteoMapComponent } from './hydrometeo-map.component';

@NgModule({
declarations: [HydroMeteoMapComponent],
imports: [CommonModule, FormsModule],
exports: [HydroMeteoMapComponent]
})
export class HydroMeteoModule {}
