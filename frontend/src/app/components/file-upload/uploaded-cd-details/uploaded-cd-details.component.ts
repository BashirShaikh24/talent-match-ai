import { SlicePipe } from '@angular/common';
import { Component, EventEmitter, Input, Output, ViewEncapsulation } from '@angular/core';
import { CandidateData, UploadType } from '../../../models';
import { TalentMatchService } from '../../../services';

@Component({
  selector: 'app-uploaded-cd-details',
  templateUrl: './uploaded-cd-details.component.html',
  styleUrl: './uploaded-cd-details.component.scss',
  encapsulation: ViewEncapsulation.None,
  imports: [SlicePipe],
})
export class UploadedCdDetailsComponent {
  @Input() uploadedFileDetails: CandidateData | null = null;
  @Output() replaceUploadedFile = new EventEmitter<boolean>();

  readonly uploadTypeEnum = UploadType;

  constructor(private talentMatchService: TalentMatchService) {}

  replaceFile() {
    this.replaceUploadedFile.emit(true);
  }

  openDetails(candidate: CandidateData) {
    this.talentMatchService.isModalOpen.set({
      state: true,
      selectedData: candidate,
      uploadedType: this.uploadTypeEnum.CD,
    });
  }
}
