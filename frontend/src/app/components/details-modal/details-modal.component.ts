import { Component, HostListener, ViewEncapsulation } from '@angular/core';
import { TalentMatchService } from '../../services';

@Component({
  selector: 'app-details-modal',
  templateUrl: './details-modal.component.html',
  styleUrl: './details-modal.component.scss',
  encapsulation: ViewEncapsulation.None,
})
export class DetailsModalComponent {
  constructor(private talentMatchService: TalentMatchService) {}

  onBackdropClick(event: MouseEvent) {
    if ((event.target as HTMLElement).classList.contains('modal-backdrop')) {
      this.onClose();
    }
  }

  onClose() {
    this.talentMatchService.isModalOpen.set({
      state: false,
      selectedData: null,
      uploadedType: '',
    });
  }

  @HostListener('document:keydown.escape')
  onEscapeKey() {
    this.onClose();
  }
}
