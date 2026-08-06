import {
  ChangeDetectorRef,
  Component,
  effect,
  ElementRef,
  HostListener,
  ViewChild,
  ViewEncapsulation,
} from '@angular/core';
import { TalentMatchService } from '../../services';

@Component({
  selector: 'app-details-modal',
  templateUrl: './details-modal.component.html',
  styleUrl: './details-modal.component.scss',
  encapsulation: ViewEncapsulation.None,
})
export class DetailsModalComponent {
  @ViewChild('modalScrollContainer') modalScrollContainer?: ElementRef<HTMLElement>;

  constructor(
    private talentMatchService: TalentMatchService,
    private cdr: ChangeDetectorRef,
  ) {
    // Scroll the modal content when the evaluated candidate is the one currently open.
    effect(() => {
      const candidateEvaluated = this.talentMatchService.isCandidateEvaluated();

      if (candidateEvaluated && !candidateEvaluated.isMatching) {
        this.scrollModalToTop();
        this.cdr.markForCheck();
      }
    });
  }

  onBackdropClick(event: MouseEvent): void {
    if ((event.target as HTMLElement).classList.contains('modal-backdrop')) {
      this.onClose();
    }
  }

  // Scroll the modal's own scrollable content area to the top.
  scrollModalToTop(): void {
    const modalScroll = this.modalScrollContainer?.nativeElement;

    if (modalScroll) {
      modalScroll.scrollTo({ top: 0, behavior: 'smooth' });
    }
  }

  // Close the modal and clear the currently selected content.
  onClose(): void {
    this.talentMatchService.isModalOpen.set({
      state: false,
      selectedData: null,
      uploadedType: '',
    });
  }

  @HostListener('document:keydown.escape')
  onEscapeKey(): void {
    this.onClose();
  }
}
