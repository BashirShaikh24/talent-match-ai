import { ComponentFixture, TestBed } from '@angular/core/testing';
import { CdDetailsComponent } from './cd-details.component';

describe('CdDetailsComponent', () => {
  let component: CdDetailsComponent;
  let fixture: ComponentFixture<CdDetailsComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [CdDetailsComponent],
    }).compileComponents();

    fixture = TestBed.createComponent(CdDetailsComponent);
    component = fixture.componentInstance;
    await fixture.whenStable();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
