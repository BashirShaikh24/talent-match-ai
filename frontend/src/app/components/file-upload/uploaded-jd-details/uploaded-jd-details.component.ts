import { Component, EventEmitter, Input, Output, ViewEncapsulation } from '@angular/core';
import { JobDescriptionData, UploadType } from '../../../models';
import { TalentMatchService } from '../../../services';

@Component({
  selector: 'app-uploaded-jd-details',
  templateUrl: './uploaded-jd-details.component.html',
  styleUrl: './uploaded-jd-details.component.scss',
  encapsulation: ViewEncapsulation.None,
})
export class UploadedJdDetailsComponent {
  @Input() uploadedFileDetails: JobDescriptionData | null = null;
  @Output() replaceUploadedFile = new EventEmitter<boolean>();

  readonly uploadTypeEnum = UploadType;

  constructor(private talentMatchService: TalentMatchService) {}

  replaceFile() {
    this.replaceUploadedFile.emit(true);
  }

  openDetails(jobDescription: JobDescriptionData) {
    this.talentMatchService.isModalOpen.set({
      state: true,
      selectedData: jobDescription,
      uploadedType: this.uploadTypeEnum.JD,
    });
  }
}
