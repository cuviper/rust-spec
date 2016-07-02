# The channel can be stable, beta, or nightly
%{!?channel: %global channel beta}

# To bootstrap from scratch, set the channel and date from src/stage0.txt
# e.g. 1.10.0 wants rustc: 1.9.0-2016-05-24
# or nightly wants some beta-YYYY-MM-DD
%bcond_without bootstrap
%global bootstrap_channel 1.9.0
%global bootstrap_date 2016-05-24

# Use "rebuild" when building with a distro rustc of the same version.
# Turn this off when the distro just has the prior release, matching bootstrap.
%bcond_without rebuild

Name:           rustc
Version:        1.10.0
Release:        0.1.beta.3%{?dist}
Summary:        The Rust Programming Language
License:        ASL 2.0, MIT
URL:            https://www.rust-lang.org

%if "%{channel}" == "stable"
%global rustc_package %{name}-%{version}
%else
%global rustc_package %{name}-%{channel}
%endif
Source0:        https://static.rust-lang.org/dist/%{rustc_package}-src.tar.gz

%if %with bootstrap
%define bootstrap_base https://static.rust-lang.org/dist/%{bootstrap_date}/%{name}-%{bootstrap_channel}
Source1:        %{bootstrap_base}-x86_64-unknown-linux-gnu.tar.gz
Source2:        %{bootstrap_base}-i686-unknown-linux-gnu.tar.gz
#Source3:        %{bootstrap_base}-armv7-unknown-linux-gnueabihf.tar.gz
#Source4:        %{bootstrap_base}-aarch64-unknown-linux-gnu.tar.gz
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
BuildRequires:  python
BuildRequires:  curl

%if %without bootstrap
%if %with rebuild
BuildRequires:  %{name} >= %{version}
%else
BuildRequires:  %{name} < %{version}
BuildRequires:  %{name} >= %{bootstrap_channel}
%endif
%endif

# make check: src/test/run-pass/wait-forked-but-failed-child.rs
BuildRequires:  /usr/bin/ps

# LLVM features are only present in x86
ExclusiveArch:      x86_64 i686

# TODO: declare remaining bundled libraries (and work on unbundling)

# ALL Rust libraries are private, because they don't keep an ABI.
%global _privatelibs lib.*-[[:xdigit:]]{8}[.]so.*
%global __provides_exclude ^(%{_privatelibs})$
%global __requires_exclude ^(%{_privatelibs})$

%description
This is a compiler for Rust, including standard libraries, tools and
documentation.


%prep
%setup -q -n %{rustc_package}

%patch1 -p1 -b .rebuild
%patch2 -p1 -b .miniz-indent
%patch3 -p1 -d src/rt/hoedown/ -b .hoedown-indent

# unbundle
rm -rf src/llvm/ src/jemalloc/

sed -i.jemalloc -e '1i // ignore-test jemalloc is disabled' \
  src/test/compile-fail/allocator-dylib-is-system.rs \
  src/test/compile-fail/allocator-rust-dylib-is-jemalloc.rs \
  src/test/run-pass/allocator-default.rs

sed -i.nomips -e '/target=mips/,+1s/^/# unsupported /' \
  src/test/run-make/atomic-lock-free/Makefile

%if %with bootstrap
mkdir -p dl/
cp -t dl/ %{SOURCE1} %{SOURCE2} # %{SOURCE3} %{SOURCE4}
%endif


%build
%define _triple_override %{_target_cpu}-unknown-linux-gnu
%configure --disable-option-checking \
  --build=%{_triple_override} --host=%{_triple_override} --target=%{_triple_override} \
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

# Shared libraries should be executable for debuginfo extraction.
find %{buildroot}/%{_libdir}/ -type f -name '*.so' -exec chmod -v +x '{}' '+'

# FIXME: __os_install_post will strip the rlibs
# -- should we find a way to preserve debuginfo?

# FIXME: we probably don't want to ship the target shared libraries
# under rustlib/ for lack of any Rust ABI.


%check
make check-lite VERBOSE=1


%post -p /sbin/ldconfig
%postun -p /sbin/ldconfig


%files
%license COPYRIGHT LICENSE-APACHE LICENSE-MIT
%doc README.md
%doc %{_docdir}/rust/
%{_bindir}/rust*
%{_libdir}/lib*
%{_libdir}/rustlib/
%{_datadir}/man/man1/rust*


%changelog
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
