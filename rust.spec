# The channel can be stable, beta, or nightly
%{!?channel: %global channel stable}

# To bootstrap from scratch, set the channel and date from src/stage0.txt
# e.g. 1.10.0 wants rustc: 1.9.0-2016-05-24
# or nightly wants some beta-YYYY-MM-DD
%bcond_with bootstrap
%global bootstrap_channel 1.9.0
%global bootstrap_date 2016-05-24

# Use "rebuild" when building with a distro rustc of the same version.
# Turn this off when the distro has the prior release, matching bootstrap.
%bcond_without rebuild

Name:           rust
Version:        1.10.0
Release:        4%{?dist}
Summary:        The Rust Programming Language
License:        ASL 2.0 or MIT, and BSD and ISC
URL:            https://www.rust-lang.org

%if "%{channel}" == "stable"
%global rustc_package rustc-%{version}
%else
%global rustc_package rustc-%{channel}
%endif
Source0:        https://static.rust-lang.org/dist/%{rustc_package}-src.tar.gz

%if %with bootstrap
%global bootstrap_base https://static.rust-lang.org/dist/%{bootstrap_date}/rustc-%{bootstrap_channel}
Source1:        %{bootstrap_base}-x86_64-unknown-linux-gnu.tar.gz
Source2:        %{bootstrap_base}-i686-unknown-linux-gnu.tar.gz
#Source3:        %{bootstrap_base}-armv7-unknown-linux-gnueabihf.tar.gz
#Source4:        %{bootstrap_base}-aarch64-unknown-linux-gnu.tar.gz
%endif

# Only x86_64 and i686 are Tier 1 platforms at this time.
# https://doc.rust-lang.org/stable/book/getting-started.html#tier-1
ExclusiveArch:  x86_64 i686
#ExclusiveArch:  x86_64 i686 armv7hl aarch64
%ifarch armv7hl
%global rust_triple armv7-unknown-linux-gnueabihf
%else
%define rust_triple %{_target_cpu}-unknown-linux-gnu
%endif

# merged for 1.11.0: https://github.com/rust-lang/rust/pull/33787
Patch1:         rust-pr33787-enable-local-rebuild.patch

# merged for 1.11.0: https://github.com/rust-lang/rust/pull/33798
Patch2:         rust-pr33798-miniz-misleading-indentation.patch

# merged for 1.11.0: https://github.com/rust-lang/hoedown/pull/6
# via https://github.com/rust-lang/rust/pull/33988
# (but eventually we should ditch this bundled hoedown)
Patch3:         rust-hoedown-pr6-misleading-indentation.patch

BuildRequires:  make
BuildRequires:  cmake
BuildRequires:  gcc
BuildRequires:  gcc-c++
BuildRequires:  llvm-devel
BuildRequires:  zlib-devel
BuildRequires:  python2
BuildRequires:  curl

%if %without bootstrap
%if %with rebuild
BuildRequires:  %{name} < %{version}-%{release}
BuildRequires:  %{name} >= %{version}
%else
BuildRequires:  %{name} < %{version}
BuildRequires:  %{name} >= %{bootstrap_channel}
%endif
%endif

# make check: src/test/run-pass/wait-forked-but-failed-child.rs
BuildRequires:  /usr/bin/ps

# TODO: work on unbundling these!
Provides:       bundled(compiler-rt) = 3.8
Provides:       bundled(hoedown) = 3.0.5
Provides:       bundled(jquery) = 2.1.4
Provides:       bundled(libbacktrace) = 6.1.0
Provides:       bundled(miniz) = 1.14

# The C compiler is needed at runtime just for linking.  Someday rustc might
# invoke the linker directly, and then we'll only need binutils.
# https://github.com/rust-lang/rust/issues/11937
Requires:       gcc

# ALL Rust libraries are private, because they don't keep an ABI.
%global _privatelibs lib.*-[[:xdigit:]]{8}[.]so.*
%global __provides_exclude ^(%{_privatelibs})$
%global __requires_exclude ^(%{_privatelibs})$

%description
Rust is a systems programming language that runs blazingly fast, prevents
segfaults, and guarantees thread safety.

This package includes the Rust compiler, standard library, and documentation
generator.


%package gdb
Summary:        GDB pretty printers for Rust
BuildArch:      noarch
Requires:       gdb

%description gdb
This package includes the rust-gdb script, which allows easier debugging of Rust
programs.


%package doc
Summary:        Documentation for Rust
# Note, while docs are mostly noarch, some things do vary by target_arch.

%description doc
This package includes HTML documentation for the Rust programming language and
its standard library.


# TODO: consider a rust-std package containing .../rustlib/$target
# This might allow multilib cross-compilation to work naturally.


%prep
%setup -q -n %{rustc_package}

%patch1 -p1 -b .rebuild
%patch2 -p1 -b .miniz-indent
%patch3 -p1 -d src/rt/hoedown/ -b .hoedown-indent

# unbundle
rm -rf src/llvm/ src/jemalloc/

# extract bundled licenses for packaging
cp src/rt/hoedown/LICENSE src/rt/hoedown/LICENSE-hoedown
sed -e '/*\//q' src/libbacktrace/backtrace.h \
  >src/libbacktrace/LICENSE-libbacktrace

# rust-gdb has hardcoded SYSROOT/lib -- let's make it noarch
sed -i.noarch -e 's#DIRECTORY=".*"#DIRECTORY="%{_datadir}/%{name}/etc"#' \
  src/etc/rust-gdb

# These tests assume that alloc_jemalloc is present
sed -i.jemalloc -e '1i // ignore-test jemalloc is disabled' \
  src/test/compile-fail/allocator-dylib-is-system.rs \
  src/test/compile-fail/allocator-rust-dylib-is-jemalloc.rs \
  src/test/run-pass/allocator-default.rs

# Fedora's LLVM doesn't support any mips targets -- see "llc -version"
sed -i.nomips -e '/target=mips/,+1s/^/# unsupported /' \
  src/test/run-make/atomic-lock-free/Makefile

%if %without bootstrap
# The hardcoded stage0 "lib" is inappropriate when using Fedora's own rustc
sed -i.libdir -e '/^HLIB_RELATIVE/s/lib$/$$(CFG_LIBDIR_RELATIVE)/' mk/main.mk
%endif

%if %with bootstrap
mkdir -p dl/
cp -t dl/ %{SOURCE1} %{SOURCE2} # %{SOURCE3} %{SOURCE4}
%endif


%build
%configure --disable-option-checking \
  --build=%{rust_triple} --host=%{rust_triple} --target=%{rust_triple} \
  %{!?with_bootstrap:--enable-local-rust %{?with_rebuild:--enable-local-rebuild}} \
  --llvm-root=/usr --disable-codegen-tests \
  --disable-jemalloc \
  --disable-rpath \
  --enable-debuginfo \
  --release-channel=%{channel}
%make_build VERBOSE=1


%install
%make_install VERBOSE=1

# Remove installer artifacts (manifests, uninstall scripts, etc.)
find %{buildroot}/%{_libdir}/rustlib/ -maxdepth 1 -type f -exec rm -v '{}' '+'

# We don't want to ship the target shared libraries for lack of any Rust ABI.
find %{buildroot}/%{_libdir}/rustlib/ -type f -name '*.so' -exec rm -v '{}' '+'

# The remaining shared libraries should be executable for debuginfo extraction.
find %{buildroot}/%{_libdir}/ -type f -name '*.so' -exec chmod -v +x '{}' '+'

# FIXME: __os_install_post will strip the rlibs
# -- should we find a way to preserve debuginfo?

# Remove unwanted documentation files (we already package them)
rm -f %{buildroot}/%{_docdir}/%{name}/README.md
rm -f %{buildroot}/%{_docdir}/%{name}/COPYRIGHT
rm -f %{buildroot}/%{_docdir}/%{name}/LICENSE-APACHE
rm -f %{buildroot}/%{_docdir}/%{name}/LICENSE-MIT

# Sanitize the HTML documentation
find %{buildroot}/%{_docdir}/%{name}/html -empty -delete
find %{buildroot}/%{_docdir}/%{name}/html -type f -exec chmod -v -x '{}' '+'

# Move rust-gdb's python scripts so they're noarch
mkdir -p %{buildroot}/%{_datadir}/%{name}
mv -v %{buildroot}/%{_libdir}/rustlib/etc %{buildroot}/%{_datadir}/%{name}/


%check
make check-lite VERBOSE=1


%post -p /sbin/ldconfig
%postun -p /sbin/ldconfig


%files
%license COPYRIGHT LICENSE-APACHE LICENSE-MIT
%license src/libbacktrace/LICENSE-libbacktrace
%license src/rt/hoedown/LICENSE-hoedown
%doc README.md
%{_bindir}/rustc
%{_bindir}/rustdoc
%{_mandir}/man1/rustc.1*
%{_mandir}/man1/rustdoc.1*
%{_libdir}/lib*
%dir %{_libdir}/rustlib
%{_libdir}/rustlib/%{rust_triple}


%files gdb
%{_bindir}/rust-gdb
%{_datadir}/%{name}


%files doc
%dir %{_docdir}/%{name}
%license %{_docdir}/%{name}/html/FiraSans-LICENSE.txt
%license %{_docdir}/%{name}/html/Heuristica-LICENSE.txt
%license %{_docdir}/%{name}/html/LICENSE-APACHE.txt
%license %{_docdir}/%{name}/html/LICENSE-MIT.txt
%license %{_docdir}/%{name}/html/SourceCodePro-LICENSE.txt
%license %{_docdir}/%{name}/html/SourceSerifPro-LICENSE.txt
%doc %{_docdir}/%{name}/html/


%changelog
* Tue Jul 26 2016 Josh Stone <jistone@redhat.com> - 1.10.0-4
- Update -doc directory ownership, and mark its licenses.
- Package and declare licenses for libbacktrace and hoedown.
- Set bootstrap_base as a global.
- Explicitly require python2.

* Tue Jul 12 2016 Josh Stone <jistone@fedoraproject.org> - 1.10.0-3
- Drop noarch from the docs, since they may vary by target_arch.
- Fixup rust-gdb so it works as noarch.

* Thu Jul 07 2016 Josh Stone <jistone@fedoraproject.org> - 1.10.0-2
- Rebuild without bootstrap.

* Thu Jul 07 2016 Josh Stone <jistone@fedoraproject.org> - 1.10.0-1
- Update to 1.10.0 (bootstrapped)
- Rename to plain "rust".
- Declare bundled provides.
- Incorporate sub-package changes from gmbonnet.

* Sat Jul 02 2016 Josh Stone <jistone@fedoraproject.org> - 1.10.0-0.1.beta.3
- Update to 1.10.0-beta.3 (bootstrapped)

* Tue Jun 03 2014 Fabian Deutsch <fabiand@fedoraproject.org> - 0.11-1
- Update to 0.11
- Add support for nightly builds

* Wed May 07 2014 Lubomir Rintel <lkundrak@v3.sk> - 0.10-2
- Use ExclusiveArch to limit supported architectures instead of forcing
  it with BuildArch
- Enable i686
- Add bootstrap sources, so that build won't access Internet
- Make it possible to build without bootstrapoing with bundled LLVM
- BuildRequire git

* Fri Apr 25 2014 Fabian Deutsch <fabiand@fedoraproject.org> - 0.10-1
- Update to 0.10

* Mon Jan 13 2014 Fabian Deutsch <fabiand@fedoraproject.org> - 0.9-1
- Update to 0.9

* Tue Oct 01 2013 Fabian Deutsch <fabiand@fedoraproject.org> - 0.8-2
- Rebuild for copr

* Fri Sep 27 2013 Fabian Deutsch <fabiand@fedoraproject.org> - 0.8-1
- Update to 0.8

* Thu Jul 04 2013 Fabian Deutsch <fabiand@fedoraproject.org> - 0.7-1
- Update to 0.7
- Introduce libextra

* Fri Apr 19 2013 Fabian Deutsch <fabiand@fedoraproject.org> - 0.6-2
- Update to rust-0.6
- Remove cargo
- Fix rpath issues differently (chrpath)

* Fri Mar 01 2013 Fabian Deutsch <fabiand@fedoraproject.org> - 0.6-1
- Initial package
