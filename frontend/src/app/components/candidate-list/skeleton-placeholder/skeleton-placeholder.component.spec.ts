import { ComponentFixture, TestBed } from '@angular/core/testing';
import { SkeletonPlaceholderComponent } from './skeleton-placeholder.component';

describe('SkeletonPlaceholderComponent', () => {
  let component: SkeletonPlaceholderComponent;
  let fixture: ComponentFixture<SkeletonPlaceholderComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [SkeletonPlaceholderComponent],
    }).compileComponents();

    fixture = TestBed.createComponent(SkeletonPlaceholderComponent);
    component = fixture.componentInstance;
    await fixture.whenStable();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
