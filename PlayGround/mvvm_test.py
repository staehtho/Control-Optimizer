from app_domain.controlsys import ExcitationTarget

if __name__ == '__main__':
    name = ExcitationTarget.REFERENCE.name
    print(ExcitationTarget[name])
