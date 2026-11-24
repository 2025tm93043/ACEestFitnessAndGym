// ACEest Fitness & Gym - Jenkins CI/CD pipeline (Assignment 2)
//
// Flow: checkout -> lint -> pytest(+coverage) -> SonarQube + quality gate -> docker build
//       -> pytest inside the container -> push to Docker Hub -> build artifacts -> (optional) deploy
//
// Jenkins prerequisites (see docs/RUNBOOK.md):
//   plugins    : Pipeline, Git, JUnit, Credentials Binding, SonarQube Scanner
//   tools      : "SonarScanner" configured under Manage Jenkins > Tools
//   system     : SonarQube server named "sonarqube" under Manage Jenkins > System
//   credentials: "dockerhub-creds" (Username+password/token), "kubeconfig" (Secret file, deploy only)
//   agent      : git, python3 + venv, docker (or podman, set CONTAINER_CLI), kubectl (deploy only)
pipeline {
    agent any

    options {
        timestamps()
        timeout(time: 40, unit: 'MINUTES')
        buildDiscarder(logRotator(numToKeepStr: '15', artifactNumToKeepStr: '15'))
        disableConcurrentBuilds()
    }

    triggers {
        // Jenkins polls GitHub every 2 minutes and builds when a new commit appears.
        pollSCM('H/2 * * * *')
    }

    parameters {
        booleanParam(name: 'RUN_SONAR', defaultValue: true,
                     description: 'Run SonarQube analysis and enforce the quality gate')
        booleanParam(name: 'PUSH_IMAGE', defaultValue: true,
                     description: 'Push the image to Docker Hub (only on the main branch)')
        choice(name: 'DEPLOY', choices: ['none', 'rolling-update'],
               description: 'Deploy the new image to Kubernetes after a successful build')
    }

    environment {
        CONTAINER_CLI = 'docker'            // set to 'podman' to build with Podman instead
        IMAGE_NAME    = 'aceest-fitness'
    }

    stages {
        stage('Clean Workspace') {
            steps { deleteDir() }
        }

        stage('Checkout') {
            steps {
                checkout scm
                script {
                    env.APP_VERSION = sh(
                        script: 'python3 -c "import version; print(version.__version__)"',
                        returnStdout: true).trim()
                    env.GIT_SHORT = sh(script: 'git rev-parse --short HEAD', returnStdout: true).trim()
                    currentBuild.displayName = "#${env.BUILD_NUMBER} v${env.APP_VERSION}"
                }
                echo "Building ACEest version ${env.APP_VERSION} (${env.GIT_SHORT})"
            }
        }

        stage('Setup Python Env') {
            steps {
                sh '''
                    python3 -m venv .venv
                    . .venv/bin/activate
                    pip install --upgrade pip
                    pip install -r requirements-dev.txt
                '''
            }
        }

        stage('Lint') {
            steps { sh '. .venv/bin/activate && python -m compileall -q . && flake8 .' }
        }

        stage('Unit Tests + Coverage') {
            steps {
                sh '''
                    . .venv/bin/activate
                    mkdir -p test-results
                    pytest --junitxml=test-results/junit.xml \
                           --cov=. --cov-report=xml:coverage.xml --cov-report=term
                '''
            }
            post {
                always { junit allowEmptyResults: true, testResults: 'test-results/junit.xml' }
            }
        }

        stage('SonarQube Analysis') {
            when { expression { params.RUN_SONAR } }
            steps {
                withSonarQubeEnv('sonarqube') {
                    sh "${tool 'SonarScanner'}/bin/sonar-scanner -Dsonar.projectVersion=${env.APP_VERSION}"
                }
            }
        }

        stage('Quality Gate') {
            when { expression { params.RUN_SONAR } }
            steps {
                // needs the SonarQube webhook  http://<jenkins>/sonarqube-webhook/
                timeout(time: 10, unit: 'MINUTES') { waitForQualityGate abortPipeline: true }
            }
        }

        stage('SonarQube Report') {
            when { expression { params.RUN_SONAR } }
            steps {
                withSonarQubeEnv('sonarqube') {
                    sh 'python3 scripts/sonar_report.py reports'
                }
            }
        }

        stage('Docker Build') {
            steps {
                sh '''
                    $CONTAINER_CLI build --target runtime -t "$IMAGE_NAME:$APP_VERSION" .
                    $CONTAINER_CLI build --target test -t "$IMAGE_NAME:$APP_VERSION-test" .
                '''
            }
        }

        stage('Tests in Container') {
            steps { sh '$CONTAINER_CLI run --rm "$IMAGE_NAME:$APP_VERSION-test"' }
        }

        stage('Push to Docker Hub') {
            when {
                allOf {
                    expression { params.PUSH_IMAGE }
                    anyOf {
                        branch 'main'
                        expression { env.GIT_BRANCH == 'origin/main' }
                    }
                }
            }
            steps {
                withCredentials([usernamePassword(credentialsId: 'dockerhub-creds',
                                                  usernameVariable: 'DH_USER',
                                                  passwordVariable: 'DH_PASS')]) {
                    sh '''
                        echo "$DH_PASS" | $CONTAINER_CLI login -u "$DH_USER" --password-stdin
                        REPO="$DH_USER/$IMAGE_NAME"
                        $CONTAINER_CLI tag "$IMAGE_NAME:$APP_VERSION" "$REPO:$APP_VERSION"
                        $CONTAINER_CLI tag "$IMAGE_NAME:$APP_VERSION" "$REPO:build-$BUILD_NUMBER"
                        $CONTAINER_CLI push "$REPO:$APP_VERSION"
                        $CONTAINER_CLI push "$REPO:build-$BUILD_NUMBER"
                        echo "Pushed $REPO:$APP_VERSION"
                    '''
                }
            }
            post {
                always { sh '$CONTAINER_CLI logout || true' }
            }
        }

        stage('Build Artifacts') {
            steps {
                sh '''
                    mkdir -p dist reports
                    git archive --format=tar.gz --prefix="aceest-fitness-$APP_VERSION/" \
                        -o "dist/aceest-fitness-$APP_VERSION.tar.gz" HEAD
                    echo "version=$APP_VERSION commit=$GIT_SHORT build=$BUILD_NUMBER" > dist/BUILD_INFO.txt
                '''
                archiveArtifacts artifacts: 'dist/*, reports/*, coverage.xml, test-results/*.xml',
                                 allowEmptyArchive: true, fingerprint: true
            }
        }

        stage('Deploy to Kubernetes') {
            when { expression { params.DEPLOY == 'rolling-update' } }
            steps {
                withCredentials([file(credentialsId: 'kubeconfig', variable: 'KUBECONFIG'),
                                 usernamePassword(credentialsId: 'dockerhub-creds',
                                                  usernameVariable: 'DH_USER',
                                                  passwordVariable: 'DH_PASS')]) {
                    sh '''
                        kubectl -n aceest set image deployment/aceest-rolling \
                            aceest="$DH_USER/$IMAGE_NAME:$APP_VERSION"
                        if ! kubectl -n aceest rollout status deployment/aceest-rolling --timeout=120s; then
                            echo "Rollout failed - rolling back to the last stable version"
                            kubectl -n aceest rollout undo deployment/aceest-rolling
                            exit 1
                        fi
                    '''
                }
            }
        }
    }

    post {
        always {
            sh '$CONTAINER_CLI rmi "$IMAGE_NAME:$APP_VERSION-test" || true'
        }
        success { echo "BUILD SUCCESS - ACEest v${env.APP_VERSION}" }
        failure { echo "BUILD FAILED - ACEest v${env.APP_VERSION}" }
    }
}
